---
layout: default
title: "betzBirdiary blog"
---

Welcome to the blog about betzBirdiary.
Besides the manuals this is intended for more easy reading about this project.
betzBirdiary is a software clon for raspberry/ bookworm to upload bird videos to the [birdiary platform](https://www.wiediversistmeingarten.org/).

# Beiträge

<ul>
  {% for post in site.posts %}
    <li>
      <a href="{{ post.url }}">{{ post.title }}</a>
      <span>({{ post.date | date: "%Y-%m-%d" }})</span>
    </li>
  {% endfor %}
</ul>
