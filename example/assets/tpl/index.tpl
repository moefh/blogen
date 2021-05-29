%{include "header"}

%{foreach post}

<div class="post">

<div class="title"><a href="${post_url}">${post_title}</a></div>
<div class="date">Posted on ${post_date}</div>
<hr>

${post_content}

<hr>
%{foreach post_tag}
<a href="${post_tag_url}">${post_tag_name}</a>
%{end}

</div>

%{end}

%{include "footer"}
