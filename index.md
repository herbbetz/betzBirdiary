---
layout: default
title: "betzBirdiary blog"
---

Welcome to the blog about betzBirdiary.
Besides the manuals this is intended for more easy reading about this project.
betzBirdiary is a software clon for raspberry/ bookworm to upload bird videos to the [birdiary platform](https://www.wiediversistmeingarten.org/).

# Beiträge

{% for post in site.posts %}
  <h2><a href="{{ post.url }}">{{ post.title }}</a></h2>
  <p>{{ post.excerpt }}</p>
{% endfor %}
