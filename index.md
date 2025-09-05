---
layout: home
title: "Welcome"
---
[About]({{ "/about" | relative_url }})

Willkommen im *betzBirdiary* Blog.
Ich versuche es hier etwas lesbarer zu gestalten als nur trockene Gebrauchsanweisungen.
*betzBirdiary* ist ein Klon für *bookworm* auf Raspberry 4/5 zum Hochladen von Vogelvideos zur [Birdiary-Plattform](https://www.wiediversistmeingarten.org/).

Welcome to the blog about *betzBirdiary*.
Besides the manuals this is intended for more easy reading about this project.
*betzBirdiary* is a software clon for *raspberry/ bookworm* to upload bird videos to the [birdiary platform](https://www.wiediversistmeingarten.org/).

**Blog Posts**
{% comment %}
- [Bookworm Bird](/betzBirdiary/posts/2025-08-09-2bookworm/)

- [betzBirdiary für bookworm (2025-08-09)]({{ "/posts/2025-08-09-2bookworm/" | relative_url }})

- html comments are displayed by jekyll, because converted to '&lt;!–'

{% endcomment %}
<ul>
{% assign posts_pages = site.pages | where_exp: "page", "page.url contains '/posts/'" %}
{% assign sorted_posts = posts_pages | sort: "date" | reverse %}
{% for post in sorted_posts %}
  <li><a href="{{ post.url | relative_url }}">{{ post.title }}</a> — {{ post.date | date: "%Y-%m-%d" }}</li>
{% endfor %}
</ul>


