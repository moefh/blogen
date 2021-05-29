<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>${blog_title}</title>
  <subtitle>${blog_subtitle}</subtitle>
  <link href="${atom_url}" rel="self"/>
  <link href="${blog_url}"/>
  <updated>${last_update_time}</updated>
  <id>${blog_url}</id>
  <author>
    <name>${blog_author}</name>
  </author>
  <generator uri="https://moefh.github.io/">BloGen<generator>
%{foreach post}
  <entry>
    <title>${post_title}</title>
    <link href="${post_url}"/>
    <id>${post_url}</id>
    <published>${post_publish_time}</published>
    <updated>${post_publish_time}</updated>
    <content type="html"><![CDATA[${post_content}]]></content>
  </entry>
%{end}
</feed>

