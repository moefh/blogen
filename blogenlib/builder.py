
import collections
import sys
import os
import shutil
import urllib.parse
import pathlib
import datetime
import re

import blogenlib
import blogenlib.source
import blogenlib.markdown
import blogenlib.template
import blogenlib.renderer

CopyFile = collections.namedtuple('CopyFile', 'src dest')

class CopyFileList:
    """List of files to be copied for the build"""

    def __init__(self):
        self.files = []

    def get_num_files(self):
        return len(self.files)

    def get_list(self):
        return self.files

    def add(self, src_file, dest_file):
        self.files.append(CopyFile(src=src_file, dest=dest_file))

    def is_source_newer(self, src, dest):
        src_path = pathlib.Path(src)
        dst_path = pathlib.Path(dest)
        if not (src_path.exists() and dst_path.exists()):
            return True
        src_stat = src_path.stat()
        dst_stat = dst_path.stat()
        if datetime.datetime.fromtimestamp(src_stat.st_mtime) > datetime.datetime.fromtimestamp(dst_stat.st_mtime):
            return True
        return False

    def copy(self, force=False, verbose=False):
        num_copied = 0
        for copy_file in self.files:
            if force or self.is_source_newer(src=copy_file.src, dest=copy_file.dest):
                if verbose:
                    print('   -> copying {}'.format(copy_file.src))
                os.makedirs(os.path.dirname(copy_file.dest), exist_ok=True)
                try:
                    shutil.copyfile(copy_file.src, copy_file.dest)
                    num_copied += 1
                except FileNotFoundError:
                    print("* WARNING: error copying '{}': file not found".format(copy_file.src))
                except:
                    print("* WARNING: error copying '{}' to '{}': {}".format(copy_file.src, copy_file.dest, sys.exc_info()[0]))
        return num_copied

class Builder:

    def __init__(self, cfg, opts):
        self.cfg = cfg
        self.opts = opts
        self.copy_files = CopyFileList()
        self.extra_pages = {}
        self.common_vars = None
        self.extra_vars = {}
        self.month_names = [
            'January', 'Ferbuary', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]

    def log(self, msg):
        if self.opts.verbose:
            print(msg)
    
    def get_tpl_file(self, tpl_name):
        return os.path.join(self.cfg.v.assets_dir, 'tpl', tpl_name + '.tpl')

    def get_publish_file(self, filename):
        return os.path.join(self.cfg.v.publish_dir, filename)
        
    def get_publish_url(self, *parts):
        return blogenlib.url_join(self.cfg.v.publish_url, *parts)
     
    def datetime_to_iso(self, dt):
        return '{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.000'.format(int(dt.year), int(dt.month), int(dt.day), int(dt.hour), int(dt.minute), int(dt.second));

    def get_dest_file_mtime(self, filename):
        path = pathlib.Path(filename)
        if not path.exists():
            return 0
        return path.stat().st_mtime
    
    def _get_common_vars(self):
        if self.common_vars:
            ret = self.common_vars.copy()
            ret.update(self.extra_vars)
            return ret
        
        self.common_vars = {
            'blog_url':         self.get_publish_url('/'),
            'favicon_url':      self.get_publish_url('/favicon.png'),
            'css_url':          self.get_publish_url('/css/style.css'),
            'blog_title':       self.cfg.v.blog_title,
            'blog_subtitle':    self.cfg.v.blog_subtitle,
            'blog_author':      self.cfg.v.blog_author,
            'blog_year':        str(datetime.datetime.now().year),
            'tag':              [],
            'month':            [],
        }
        for tag in self.src.get_tag_list():
            self.common_vars['tag'].append({
                'tag_name': tag,
                'tag_url':  self.get_publish_url('/tags', tag),
            })
        for month in self.src.get_month_list():
            (y, m) = month.split('-')
            month_name = '{} {}'.format(self.month_names[int(m)-1], y)
            self.common_vars['month'].append({
                'month_name': month_name,
                'month_url':  self.get_publish_url('/archives/', month.replace('-', '/')),
            })
        return self._get_common_vars()

    def _get_post_vars(self, post):
        data = {
            'post_url':      post.get_publish_url(),
            'post_title':    post.get_title(),
            'post_date':     post.get_date(),
            'post_content':  post.get_html(),
            'post_tag':      []
        }
        for tag in post.get_tags():
            data['post_tag'].append({
                'post_tag_url':  self.get_publish_url('tags', tag),
                'post_tag_name': '#' + tag,
            })
        return data
    
    def _write_file(self, filename, content):
        self.log('   -> writing {}'.format(filename))
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            f.write(content)
        self.num_files_written += 1
            
    def _build_single_page(self, page, tpl_name, filename):
        if ((not self.opts.force_rebuild) and (not page.needs_update())):
            return
        data = self._get_common_vars()
        data.update({
            'page_title':   page.get_title(),
            'page_date':    page.get_date(),
            'page_content': page.get_html(),
        })
        content = self.tpl.build(tpl_name, data)
        self._write_file(filename, content)
        
    def _build_post_page(self, post):
        if ((not self.opts.force_rebuild) and (not post.needs_update())):
            return
        older_post = post.get_older_post()
        newer_post = post.get_newer_post()
        data = self._get_common_vars()
        post_data = self._get_post_vars(post)
        post_data.update({
            'older_post_url':   older_post.get_publish_url() if older_post else '',
            'older_post_title': older_post.get_title() if older_post else '',
            'newer_post_url':   newer_post.get_publish_url() if newer_post else '',
            'newer_post_title': newer_post.get_title() if newer_post else '',
        })
        data.update(post_data)

        content = self.tpl.build('post', data)
        filename = os.path.join(post.get_publish_dir(), 'index.html')
        self._write_file(filename, content)

    def _build_post_list_page(self, post_list, tpl_name, filename, page_nav, extra_vars=None):
        data = self._get_common_vars()
        data.update({
            'prev_page_url': page_nav['prev_url'],
            'next_page_url': page_nav['next_url'],
            'page_num':      page_nav['page_num'],
            'num_pages':     page_nav['num_pages'],
            'post':          []
        })
        if extra_vars:
            data.update(extra_vars)
        for post in post_list:
            data['post'].append(self._get_post_vars(post))
        
        content = self.tpl.build(tpl_name, data)
        self._write_file(filename, content)

    def _build_post_list(self, post_list, tpl_name, num_posts_in_page, page_filenames, extra_vars=None):
        if ((not self.opts.force_rebuild) and
            (self.src.get_last_post_mtime() < self.get_dest_file_mtime(self.get_publish_file(page_filenames['first'])))):
            return
        num_pages = len(post_list) // num_posts_in_page
        if len(post_list) % num_posts_in_page != 0:
            num_pages += 1
            
        prev_page_url = ''
        cur_page_url = self.get_publish_url(page_filenames['first'])
        cur_page = 0
        while cur_page < num_pages:
            first_post = cur_page*num_posts_in_page
            end_post  = min((cur_page+1)*num_posts_in_page, len(post_list))
            next_page_url = self.get_publish_url(page_filenames['rest'].format(cur_page+2))
            page_nav = {
                'page_num':  str(cur_page + 1),
                'num_pages': str(num_pages),
                'prev_url':  prev_page_url,
                'next_url':  next_page_url if (cur_page+1)*num_posts_in_page < len(post_list) else ''
            }
            out_file = page_filenames['first'] if cur_page == 0 else page_filenames['rest'].format(cur_page+1)
            self._build_post_list_page(post_list[first_post:end_post], tpl_name, self.get_publish_file(out_file), page_nav, extra_vars=extra_vars)
            prev_page_url = cur_page_url
            cur_page_url = next_page_url
            cur_page += 1

    def _build_tag_pages(self):
        for tag in self.src.get_tag_list():
            page_filenames = {
                'first': blogenlib.url_join('tags', tag, 'index.html'),
                'rest':  blogenlib.url_join('tags', tag, 'page{}.html'),
            }
            data = {
                'tag_name': tag
            }
            post_list = sorted(self.src.get_tag_posts(tag), reverse=True, key=lambda post: post.get_date())
            self._build_post_list(post_list, 'tag', self.cfg.int('posts_in_tag_page', defval=5), page_filenames, extra_vars=data)

    def _build_month_pages(self):
        for month in self.src.get_month_list():
            (y, m) = month.split('-')
            month_name = '{} {}'.format(self.month_names[int(m)-1], y)
            page_filenames = {
                'first': blogenlib.url_join('archives', month.replace('-', '/'), 'index.html'),
                'rest':  blogenlib.url_join('archives', month.replace('-', '/'), 'page{}.html'),
            }
            data = {
                'month_name': month_name
            }
            post_list = sorted(self.src.get_month_posts(month), reverse=True, key=lambda post: post.get_date())
            self._build_post_list(post_list, 'month', self.cfg.int('posts_in_month_page', defval=5), page_filenames, extra_vars=data)

    def _build_atom_feed(self):
        filename = self.get_publish_file('atom.xml')
        if ((not self.opts.force_rebuild) and
            (self.src.get_last_post_mtime() < self.get_dest_file_mtime(filename))):
            return

        data = self._get_common_vars()
        post_list = self.src.get_post_list()
        data.update({
            'blog_url':         blogenlib.url_join(self.cfg.v.site_url, self.cfg.v.publish_url) + '/',
            'atom_url':         blogenlib.url_join(self.cfg.v.site_url, self.cfg.v.publish_url, 'atom.xml'),
            'last_update_time': self.datetime_to_iso(post_list[0].get_date_time()),
            'post':             [],
        })
        num_posts = min(len(post_list), int(self.cfg.v.posts_in_atom_feed))
        for post in post_list[0:num_posts]:
            data['post'].append({
                'post_url':          blogenlib.url_join(self.cfg.v.site_url, self.cfg.v.publish_url, post.get_publish_url()) + '/',
                'post_title':        post.get_title(),
                'post_date':         post.get_date(),
                'post_publish_time': self.datetime_to_iso(post.get_date_time()),
                'post_content':      post.get_html(),
            })

        filename = self.get_publish_file('atom.xml')
        content = self.tpl.build('atom', data)
        self._write_file(filename, content)
            
    def _add_static_assets(self):
        def add_assets(root, prefix):
            for name in os.listdir(root):
                prefixed_name = os.path.join(prefix, name)
                filename = os.path.join(root, name)
                if os.path.isdir(filename):
                    add_assets(filename, prefixed_name)
                elif os.path.isfile(filename):
                    self.copy_files.add(filename, prefixed_name)
        add_assets(os.path.join(self.cfg.v.assets_dir, 'static'), self.cfg.v.publish_dir)
                    
    def _set_page_link_vars(self):
        if self.cfg.enabled('build_archives'):
            self.extra_vars['archives_url'] = self.get_publish_url('/archives')
        if self.cfg.enabled('build_atom'):
            self.extra_vars['atom_url']     = self.get_publish_url('/atom.xml')
        for name, page in self.src.get_page_map().items():
            self.extra_vars[name + '_url']  = page.get_publish_url()

    def _render_pages(self):
        self.log("-> parsing sources")
        for page_list in [ self.src.get_post_list(), self.src.get_page_list() ]:
            for page in page_list:
                self.log("   -> parsing {}".format(page.get_source_filename()))
                markdown = self.parser.parse(page.get_text())
                page.set_html(self.renderer.render(markdown))

    def _output(self):
        self.log("-> building output")
        self.num_files_written = 0
        for post in self.src.get_post_list():
            self._build_post_page(post)
        for page in self.src.get_single_page_list():
            if self.opts.force_rebuild or page.needs_update():
                self._build_single_page(page, 'single_page', os.path.join(page.get_publish_dir(), 'index.html'))
        self._build_post_list(self.src.get_post_list(), 'index', self.cfg.int('posts_in_index_page', defval=5), { 'first' : 'index.html', 'rest': 'page{}.html' })
        if self.cfg.enabled('build_archives'):
            self._build_post_list(self.src.get_post_list(), 'archives', self.cfg.int('posts_in_archive_page', defval=5), { 'first' : 'archives/index.html', 'rest': 'archives/page{}.html' })
        if self.cfg.enabled('build_months'):
            self._build_month_pages()
        if self.cfg.enabled('build_tags'):
            self._build_tag_pages()
        if self.cfg.enabled('build_atom'):
            self._build_atom_feed()
        self.log('   -> {} files built'.format(self.num_files_written))
    
        self.log('-> copying files')
        num_files = self.copy_files.copy(force=self.opts.force_rebuild, verbose=self.opts.verbose)
        self.log('   -> {} files copied'.format(num_files))

    def build(self):
        self.log("-> reading sources")
        self.src = blogenlib.source.Source(self.cfg)
        self.parser = blogenlib.markdown.Parser()
        self.tpl = blogenlib.template.TemplateProcessor(os.path.join(self.cfg.v.assets_dir, 'tpl'))
        self.renderer = blogenlib.renderer.Renderer(self.cfg, self.src, self.copy_files)

        self._set_page_link_vars()
        self._add_static_assets()
        self._render_pages()
        self._output()
