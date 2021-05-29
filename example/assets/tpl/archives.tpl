%{include "header"}

%{foreach post}

<p><a href="${post_url}">${post_title}</a></p>
<p>Posted on${post_date}</p>
<p></p>

%{end}

%{include "footer"}
