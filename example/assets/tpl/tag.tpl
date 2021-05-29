%{include "header"}

<p>Posts tagged "<b>${tag_name}</b>":</p>

%{foreach post}

<div class="post">
<p><a href="${post_url}">${post_title}</a></p>
<p>Posted on${post_date}</p>
</div>

%{end}

%{include "footer"}
