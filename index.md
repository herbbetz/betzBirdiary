---
layout: home
title: "betzBirdiary blog"
---
[About]({{ "/about" | relative_url }})

Willkommen im *betzBirdiary* Blog.
Ich versuche es hier etwas lesbarer zu gestalten als nur trockene Gebrauchsanweisungen.
*betzBirdiary* ist ein Klon für *bookworm* auf Raspberry 4/5 zum Hochladen von Vogelvideos zur [Birdiary-Plattform](https://www.wiediversistmeingarten.org/).

Welcome to the blog about *betzBirdiary*.
Besides the manuals this is intended for more easy reading about this project.
*betzBirdiary* is a software clon for *raspberry/ bookworm* to upload bird videos to the [birdiary platform](https://www.wiediversistmeingarten.org/).

**Blog Posts**

{% assign all_posts = site.posts_folder | sort: "date" | reverse %}
<ul>
  {% for post in all_posts %}
    <li>
      <a href="{{ post.url }}">{{ post.title }}</a>
    </li>
  {% endfor %}
</ul>
