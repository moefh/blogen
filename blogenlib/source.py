
import collections
import re
import os
import pathlib

import blogenlib

PostDateTime = collections.namedtuple('PostDateTime', 'date time year month day hour minute second')

class Page:

    def __init__(self, filename, cfg):
        self.source_filename = filename
        self.source_dir = os.path.dirname(filename)
        self.name = os.path.basename(self.source_dir)
        self.publish_dir = os.path.join(cfg.v.publish_dir, self.name)
        self.publish_url = blogenlib.url_join(cfg.v.publish_url, self.name)
        self.mtime = os.stat(filename).st_mtime
        self.read(filename)

    def get_name(self):
        return self.name

    def get_mtime(self):
        return self.mtime
    
    def get_source_filename(self):
        return self.source_filename

    def get_source_dir(self):
        return self.source_dir
        
    def get_publish_dir(self):
        return self.publish_dir

    def get_publish_url(self):
        return self.publish_url

    def get_text(self):
        return self.text

    def get_title(self):
        return self.header['title']

    def get_tags(self):
        return self.header['tags']

    def get_date_time(self):
        return self.header['date_time']

    def get_date(self):
        return self.header['date_time'].date

    def get_time(self):
        return self.header['date_time'].time

    def set_html(self, html):
        self.html = html

    def get_html(self):
        return self.html

    def read(self, filename):
        with open(filename, 'r') as f:
            self.header = self.read_header(f)
            self.text = f.read()
    
    def needs_update(self):
        dest_file = os.path.join(self.get_publish_dir(), 'index.html')
        dest_path = pathlib.Path(dest_file)
        #print("-> checking {} -> {}".format(self.source_filename, dest_file))
        if not dest_path.exists():
            return True
        dest_mtime = os.stat(dest_file).st_mtime
        return self.mtime > dest_mtime

    def dump(self):
        print("------")
        print("title: {}".format(self.title))
        print("date: {}".format(self.date))
        print("tags:")
        for tag in self.tags:
            print('- {}'.format(tag))
        print("------")
        print(self.text)

    def read_header_data(self, f):
        sep = f.readline().strip()
        data = {}
        cur_name = None
        while True:
            line = f.readline()
            if line == '':
                raise Exception('non-terminated header')
            line = line.strip()

            if line == sep:
                break
            
            if line.endswith(':'):
                cur_name = line[0:-1]
                data[cur_name] = []
                continue
            
            if line.startswith('-'):
                if cur_name is None:
                    raise Exception('item outside list')
                data[cur_name].append(line[1:].strip())
                continue

            parts = line.split(':', maxsplit=1)
            if len(parts) == 1:
                raise Exception('invalid header line: ' + line)
            data[parts[0].strip()] = parts[1].strip()
        return data

    def read_header(self, f):
        data = self.read_header_data(f)
        ret = {}
        ret['title'] = data['title'] if 'title' in data else ''
        ret['tags']  = data['tags']  if 'tags'  in data else []
        ret['date_time'] = self.read_date_time(data)
        return ret

    def read_date_time(self, data):
        text = data['date'] if 'date' in data else ''

        year   = '2001'
        month  = '01'
        day    = '01'
        hour   = '00'
        minute = '00'
        second = '00'
        
        match = re.fullmatch(r'(\d+)-(\d+)-(\d+)\s+(\d+):(\d+):(\d+)', text)
        if match:
            year   = match.group(1)
            month  = match.group(2)
            day    = match.group(3)
            hour   = match.group(4)
            minute = match.group(5)
            second = match.group(6)

        match = re.fullmatch(r'(\d+)-(\d+)-(\d+)', text)
        if match:
            year  = match.group(1)
            month = match.group(2)
            day   = match.group(3)
        
        return PostDateTime(date='{}-{}-{}'.format(year, month, day), time='{}:{}:{}'.format(hour, minute, second),
                            year=year, month=month, day=day,
                            hour=hour, minute=minute, second=second)

class Post(Page):

    def __init__(self, filename, cfg):
        Page.__init__(self, filename, cfg)
        self.cfg = cfg
        self.source_dir = filename[:-3]  # strip '.md' from end
        self.name = os.path.basename(self.source_dir)
        pdt = self.get_date_time()
        self.publish_dir = os.path.join(self.cfg.v.publish_dir, pdt.year, pdt.month, pdt.day, self.get_name())
        self.publish_url = blogenlib.url_join(self.cfg.v.publish_url, pdt.year, pdt.month, pdt.day, self.get_name())
        self.newer_post = None
        self.older_post = None

    def get_newer_post(self):
        return self.newer_post

    def get_older_post(self):
        return self.older_post

    def set_sibling_posts(self, older, newer):
        self.older_post = older
        self.newer_post = newer
    
class Source:

    def __init__(self, cfg):
        self.cfg = cfg

        self.page_list = []
        self.page_map = {}
        
        self.post_list = []
        self.post_tree = {}
        self.post_map = {}
        
        self.tag_set = set()
        self.posts_by_tag = {}
        self.tag_list = []

        self.month_set = set()
        self.posts_by_month = {}
        self.month_list = []

        self.single_page_list = []
        self.single_page_map = {}

        self.last_post_mtime = 0
        
        self.read()
        
    def dump(self):
        ret = []
        def dump_tree(key, val, indent):
            if isinstance(val, Page):
                ret.append('{}\-- {}'.format(indent, key, val.get_title()))
            else:
                ret.append('{}\-- {}'.format(indent, key))
                for k, v in val.items():
                    dump_tree(k, v, indent+'    ')
        ret.append('ROOT')
        for k, v in self.post_tree.items():
            dump_tree(k, self.v, '')
        return '\n'.join(ret)
        
    def get_page_list(self):
        return self.page_list

    def get_page_map(self):
        return self.page_map
    
    def get_page(self, name):
        return self.page_map.get(name, None)

    def get_single_page_list(self):
        return self.single_page_list

    def get_single_page(self, name):
        return self.single_page_map.get(name, None)
    
    def get_post_list(self):
        return self.post_list
        
    def get_post_map(self):
        return self.post_map

    def get_post(self, name):
        return self.post_map.get(name, None)

    def get_tag_list(self):
        return self.tag_list

    def get_tag_posts(self, tag):
        return self.posts_by_tag[tag]
    
    def get_month_list(self):
        return self.month_list

    def get_month_posts(self, month):
        return self.posts_by_month[month]

    def get_last_post_mtime(self):
        return self.last_post_mtime
    
    def _add_page(self, page):
        self.page_map[page.get_name()] = page
        self.page_list.append(page)

    def _add_single_page(self, page):
        self._add_page(page)
        self.single_page_map[page.get_name()] = page
        self.single_page_list.append(page)

    def _add_post(self, post):
        self._add_page(post)
        
        post_name = post.get_name()
        post_dt = post.get_date_time()

        # add post to map
        if post_name in self.post_map:
            raise Exception('post "{}" already exists'.format(post_name))
        self.post_map[post_name] = post
        self.post_list.append(post)
        
        # add post to tree
        pdt = post.get_date_time()
        path = [ pdt.year, pdt.month, pdt.day ]
        node = self.post_tree
        for p in path:
            if p not in node:
                node[p] = {}
            node = node[p]
        node[post_name] = post

        # add post in month list
        month = '{}-{}'.format(post_dt.year, post_dt.month)
        self.month_set.add(month)
        if month not in self.posts_by_month:
            self.posts_by_month[month] = set()
        self.posts_by_month[month].add(post)
        
        # add post in tag list
        for tag in post.get_tags():
            self.tag_set.add(tag)
            if tag not in self.posts_by_tag:
                self.posts_by_tag[tag] = set()
            self.posts_by_tag[tag].add(post)

    def _read_posts(self):
        posts_source_dir = os.path.join(self.cfg.v.source_dir, '_posts')
        for name in os.listdir(posts_source_dir):
            filename = os.path.join(posts_source_dir, name)
            if filename.endswith('.md') and os.path.isfile(filename):
                self._add_post(Post(filename, self.cfg))

        # sort list and mark siblings
        self.post_list.sort(reverse=True, key=lambda post: post.get_date())
        for num, post in enumerate(self.post_list):
            older = self.post_list[num+1] if num+1 < len(self.post_list) else None
            newer = self.post_list[num-1] if num > 0 else None
            post.set_sibling_posts(older, newer)

        self.month_list = sorted(self.month_set, reverse=True)
        self.tag_list = sorted(self.tag_set)

    def _read_single_pages(self):
        for name in os.listdir(self.cfg.v.source_dir):
            if name.startswith('_'):
                continue
            filename = os.path.join(self.cfg.v.source_dir, name, 'index.md')
            if not os.path.exists(filename):
                continue
            page = Page(filename, self.cfg)
            self._add_single_page(page)
        
    def read(self):
        self._read_posts()
        self._read_single_pages()

        last_post_mtime = 0
        for post in self.post_list:
            post_mtime = post.get_mtime()
            if last_post_mtime < post_mtime:
                last_post_mtime = post_mtime
        self.last_post_mtime = last_post_mtime
