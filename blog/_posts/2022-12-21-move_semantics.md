---
layout: post_blog
title: "You Don’t Know C++ Until You Know About Move Semantics"
author: Richard Hu
tags:
- C++
- move semantics
- value categories
- lvalue references
- rvalue references
- std::move
excerpt_separator: <!--more-->
---
{% seo %}

Move semantics are a fundamental component of object lifecycle and effective memory management in C++, and writing good C++ code goes hand in hand with understanding move semantics.<!--more-->

In this post, I motivate the existence of move semantics and dive into the basic technical details behind moving objects in C++.

| **Contents**|
|:--------|
| 1. [Why Are Move Semantics Useful?](#why-are-move-semantics-useful) |
| 2. [Value Categories in Modern C++](#value-categories-in-modern-c) |
| 3. [How References *Actually* Work (Mostly)](#how-references-actually-work-mostly) |
| 4. [Implementing Move Semantics](#implementing-move-semantics) |
| 5. [Conclusion](#conclusion) |
| 6. [References](#references) |

<h3 id="why-are-move-semantics-useful">Why Are Move Semantics Useful? <a href="#top">⇱</a></h3>

Let's say I was a particularly precocious baby and on my first birthday, I wanted to write some C++ code to fill a `vector<int>` with a Python-like range of `int`s. The date would have been October 15th 2002, meaning that the most up-to-date C++ standard would have been C++ 98 and my code might have looked like this:

```c++
vector<int> range(int start, int end, int increment) {
    vector<int> res;
    for (int i = 0; start + i * increment < end; i++)
            res.push_back(start + i * increment);
    return res;
}
```

Seems fine so far. Now let's try the function out.

```c++
vector<int> every_three = range(0, 20, 3);
cout << "Some numbers equivalent to 1 mod 3" << endl;
# No range-based for loops in C++ 98 :(
for (int i = 0; i < every_three.size(); i++)
    cout << every_three[i] + 1 << endl;
```

Something annoying happens here, but can you spot what it is? Let's analyze that very first line. 

`every_three` is *copy-constructed* from the return value of the call to `range()`. Inside the call to `range()`, the `vector<int> res` is created, filled, and returned. Let's assume the compiler is smart and avoids copying `res` to a temporary variable so before `every_three`'s copy constructor is called, there is already memory allocated for `range()`'s return value.

Then, within `every_three`'s copy constructor, *memory is allocated again* for `every_three` and all the elements of `range()`'s return value are copied to `every_three`'s memory.

Clearly, this is inefficient. We'd much rather just *move* the data from the return value to `every_three` since the return value isn't going to be used for anything else anyways; it's a temporary variable so the compiler will probably just destroy it right after this line.

The C++ Standard Committee recognized the importance of being able to moving objects around and so with C++ 11, *move semantics* were introduced.

<h3 id="value-categories-in-modern-c">Value Categories in Modern C++ <a href="#top">⇱</a></h3>

*Value categories* govern the rules of moving and every expression in C++ (e.g. variable names, literals, function calls, operators with operands) belongs to a value category. Because value categories are associated with the expression itself and not the object that is the result of evaluating the expression, they are known at compile-time.

C++ 11 redefined and expanded on the older value categories and the C++ reference has [a comprehensive page about them](https://en.cppreference.com/w/cpp/language/value_category), but I think it also helps to have an intuitive understanding of the expressions that belong in each value category.

Broadly, expressions in C++ can either have an identity or not have an identity and you are either able or unable to move the result of evaluating an expression. It might not be easy to see why these attributes are orthogonal (shouldn't we only be able to move temporary, identity-less objects that we know we will never use again?) so here is a motivating example. Consider the following class:

```c++
class A {
public:
    A(int size, int value) : v(size, value) { }
    // ... functions that may modify this->v
    vector<int> v;
};
```

Let's begin with a simple case.

```c++
A a1(5, 1);
A a2 = a1;
```

`a1` has a name and identity and therefore, the compiler should not move it to `a2` here since it might be used later on. Of course, we should have some way to explicitly tell the compiler we want to move it (perhaps because we know it will never be used again) but since we don't do anything like that here, the compiler should play it safe and copy `a1` to `a2`.

```c++
A a3 = A(5, 1);
```

`A(5, 1)`, on the other hand, has no identity. It evaluates to a temporary object that will be destroyed as soon as the line finishes executing so the compiler, ideally, should move it to `a3` instead of copying it.

```c++
vector<int> v = A(5, 1).v
```

`A(5, 1).v` has an identity because it is named but, clearly, the compiler should still move it since it is a member of a temporary object that will be destroyed soon.

Thus, C++ places every expression into a value category based on whether it has an identity and whether the object it evaluates to can be moved. The 3 *primary categories* are lvalues, xvalues, and prvalues and, intuitively, they are defined like so:

<img style="display: block; 
           margin-left: auto;
           margin-right: auto;
           width: 50%;"
    src="/assets/blog/2022-12-21-move_semantics/basic_value_categories.svg" 
    alt="Basic Value Categories">

The concept of an expression that has no identity but also cannot be moved has no practical use so C++ has no value category for them. Here are the value categories of some of the aforementioned expressions:

```c++
A a1(5, 1); // a1 is an lvalue.
A a2 = a1;  // a2 is an lvalue.
A(5, 1);    // A(5, 1) is a prvalue.
A(5, 1).v;  // A(5, 1).v is an xvalue
```

On top of these three basic value categories, C++ also defines 2 more *mixed categories*—glvalues and rvalues—which indicate that an expression has an identity or can be moved, respectively.

<img style="display: block; 
           margin-left: auto;
           margin-right: auto;
           width: 50%;"
    src="/assets/blog/2022-12-21-move_semantics/all_value_categories.svg" 
    alt="Basic Value Categories">

Finally, the names of the value categories do all have meanings.
*   lvalue - the 'l' stands for "left." Prior to C++ 11, lvalues were just expressions with an identity and only lvalues could appear on the left side of the assignment operator `=`
*   xvalue - short for "eXpiring value". You can think of them as named expressions that are about to be destroyed, so they are fine to move.
*   prvalue - short for "pure rvalue". These are expressions that generally evaluate to nameless, temporary objects (e.g. `"hello"`, `A(5, 1)`, or `a + b`).
*   glvalue - short for "generalized lvalue". Anything with a name falls into here.
*   rvalue - the 'r' stands for "right." Prior to C++ 11, rvalues were just expressions with no identity and they could only appear on the right side of the assignment operator `=`

<h3 id="how-references-actually-work-mostly">How References <em>Actually</em> Work (Mostly) <a href="#top">⇱</a></h3>

If you took an intro CS course that used C++, you probably thought of references as just a way to "refer" to another variable and never considered them further. However, references are closely tied to value categories and understanding them is crucial to understanding move semantics.

Most of the time, the only value categories we care about are lvalues and rvalues, since rvalues are things that can be moved and lvalues are everything else. As such, in C++, we can bind a reference to either an lvalue or an rvalue with a single ampersand `&` or a double ampersand `&&`, respectively.

```c++
int a = 1;
int b& = a;     // lvalue reference
a = 2;          // a == b == 2
b = 3;          // a == b == 3

int&& c = 1;    // rvalue reference (useless for now)

int& d = 1;     // compiler error: can't bind lvalue reference to rvalue
int&& e = a;    // compiler error: can't bind rvalue reference to lvalue
```

Additionally, if we add a `const` in front of an lvalue reference, *the resulting reference will bind to both lvalues and rvalues*, since the `const` modifier prevents the name from being reassigned. The same does not hold for rvalue references though.

```c++
int a = 1;
const int& b = a;   // ok!
const int& c = 1;   // also ok! We can't reassign c anyways.

const int&& d = a;  // compiler error: can't bind rvalue reference to lvalue
const int&& e = 1;  // ok!
```

lvalue and rvalue references are powerful because they enable us to achieve polymorphism based on value categories.

```c++
void f(int& n) { cout << 1 << endl; }
void f(int&& n) { cout << 2 << endl; }

int a = 1;
f(a);   // prints 1 because a is an lvalue
f(2);   // prints 2 because 2 is an rvalue
```

Because C++'s overload resolution picks the most "specific" signature for a function call's arguments, behaviour is still predictable when we add `const` lvalue references into the mix.

```c++
void f(int& n) { cout << 1 << endl; }
void f(const int& n) { cout << 2 << endl; }

int a = 1;
const int b = 2;
f(a);   // prints 1 because a is a non-const lvalue
f(b);   // prints 2 because b is a const lvalue
f(2);   // prints 2 because 2 is an rvalue
```

It is important to note that within the scope of the function `f`, `n` itself is an lvalue because it has an identity and is not short-lived; it just could be the case that it is bound to an rvalue.

With polymorphism alongside lvalue and rvalue references, we can guarantee that function arguments are bound to a particular value category, meaning that we can dictate a function's behaviour based on whether or not its arguments can be moved!

One last thing to note: **the double ampersand `&&` does not always indicate an rvalue reference.** Specifically, if the `&&` is attached to a template parameter or `auto`, it means something very different.

```c++
template<typename T>
void f(T&&);    // NOT AN RVALUE REFERENCE

const int a = 1;
auto&& b = a;   // NOT AN RVALUE REFERENCE
```

Read up on template type deduction and forwarding references to learn more about this important caveat.

<h3 id="implementing-move-semantics">Implementing Move Semantics <a href="#top">⇱</a></h3>

C++ 11 introduced two new special member functions: the move constructor and the move assignment operator. Like the other special member functions, default versions are provided if not explicitly defined and you can explicitly request them with `= default` or disable them with `= delete`.

```c++
class A {
public:
    ~A();                   // destructor

    A(const A&);            // copy constructor
    A& operator=(const A&); // copy assignment operator

    A(A&&);             // NEW in C++ 11: move constructor
    A& operator=(A&&);  // NEW in C++ 11: move assignment operator
};
```

We can see that when an object is constructed or assigned from an rvalue reference, the move operations are used if they are available so we can override them to more efficiently handle construction and assignment from objects that we know are okay to move.

```c++
class A {
public:
    // ... other functions
    A(A&& other) {
        // Take other's resources
        this->arr = other.arr;
        this->size = other.size;
    }

    A& operator=(A&& other) {
        // Clean up my own resources first
        delete[] this->arr;

        // Then, take other's resources
        this->arr = other.arr;
        this->size = other.size;

        return *this;
    }
    int* arr;
    int size;
};
```

In the example `A` class, the copy operations would have to allocate memory for `this->arr` and then copy the contents of `other.arr` over element-by-element. Clearly, when `other` is fine to move, we'd rather just give its resources to `this` directly instead of wasting memory by copying them over.

```c++
A make_A(int);      // some factory function

A a = make_A(3);    // make_A(3) is an rvalue so move constructor is called.
// ... do some stuff
a = make_A(7);      // make_A(7) is an rvalue so move assignment operator is called.
```

Moreover, if we want to explicitly move an object that is an lvalue expression, we can call `std::move()`.

```c++
A a1();
A a2 = move(v1);
```

`std::move()` doesn't actually move anything on its own, it just casts its argument to an rvalue reference using a `static_cast()` and lets overload resolution do the rest. You should always explicitly call `std::move()` to move an lvalue expression, but also know that most modern compilers are quite intelligent and will try to turn copy operations into move operations whenever possible.

Lastly, it may be tempting to define move operations for every user-defined `class` you write, but you should be wary of making your code needlessly complex. The default move operations already perform a move operation on all of an object's member variables so you should only override the move operations if you desire more specific move semantics. This is one part of the [rule of five](https://en.cppreference.com/w/cpp/language/rule_of_three#Rule_of_five).

<h3 id="conclusion">Conclusion <a href="#top">⇱</a></h3>

This post barely scratches the surface of move semantics; there are [entire books](https://www.cppmove.com/) dedicated to explaining all of its tiny little details and nuances.

The bottom line, though, is that move semantics enable you to elegantly hand off objects and their resources and they are a fundamental tool for optimizing code performance.

You don't know C++ until you know about move semantics; but once you have even a basic understanding of them, you can begin to effectively leverage one of C++'s most powerful features to create fast, robust, and efficient programs.

<h3 id="references">References <a href="#top">⇱</a></h3>

**[1]** Bjarne Stroustrup, *A Tour of C++ (Second edition)*, 2018

**[2]** Scott Meyers, *Effective Modern C++*, 2014

**[3]** Anders Schau Knatten, [lvalues, rvalues, glvalues, prvalues, xvalues, help!](https://blog.knatten.org/2018/03/09/lvalues-rvalues-glvalues-prvalues-xvalues-help/), 2018-03-09

**[4]** Alex Allain, [Move semantics and rvalue references in C++11](https://www.cprogramming.com/c++11/rvalue-references-and-move-semantics-in-c++11.html)

**[5]** Arthur O’Dwyer, [“Universal reference” or “forwarding reference”?](https://quuxplusone.github.io/blog/2022/02/02/look-what-they-need/), 2022-02-02

**[6]** [C++ reference](https://en.cppreference.com/w/cpp)
