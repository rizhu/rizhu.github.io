---
layout: default
---
{% seo %}

## Blog

Occasional blog posts about interesting stuff that pops into my head.

{% for post in site.categories.blog %}

* * *
<span style="font-size:larger;">**[{{ post.title }}]({{ post.url }})**</span>
<br>
*{{ post.date | date: "%B %-d, %Y" }}*
{{ post.excerpt }}
<p style="font-size:smaller;">tags:&ensp;
{% for tag in post.tags %}
<em>{{ tag }}</em>&ensp;
{% endfor %}</p>

{% endfor %}
