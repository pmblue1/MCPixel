import json
import datetime
import requests
import os






def xml_item_sep(txt,name):
    a = txt.split(f"<{name}>")
    a.pop(0)
    b = []
    for x in a:
        if f"</{name}>" in x:
            b.append(x.split(f"</{name}>")[0])
    return b

def get_between(txt,s,e):
    a = txt.split(s)
    a.pop(0)
    b = []
    for x in a:
         b.append(x.split(e)[0])
    return b
    

def xml_item_get(txt,name):
    a = txt.split(f"<{name}")
    a.pop(0)
    b = []
    for x in a:
        if f">" in x[0]:
            b.append(x.split(f"</")[0][1:])
    return b

def date_parse(raw):
    return datetime.datetime.strptime(raw,"%a, %d %b %Y %H:%M:%S %z")


def class_name(c):
    if not callable(c):
        rs = repr(c.__class__)
    else:
        rs = repr(c)
    if "class '" in rs:
        if "." in rs:
            return rs.split("'")[1].split(".",1)[1]
        return rs.split("'")[1]
    return rs


class HypixelForums:
    load_categories = False
    rss = "https://hypixel.net/forums/-/index.rss"
    class Thread:
        def from_dict(d):
            a = HypixelForums.Thread("",blank=True)
            a.title = d["title"]
            a.content = d["content"]
            a.url = d["url"]
            dt = datetime.datetime.fromtimestamp(d["date"])
            a.date_raw = dt.strftime("%a, %d %b %Y %H:%M:%S %z")
            a.date = dt
            a.id = d["id"]
            a.author = d["author"]
            a.category = HypixelForums.BaseCategory.get_category(d["category"])
            return a
        def __init__(self,x,category=None,blank=False):
            if blank:
                return
            self.title = xml_item_get(x,"title")[0].replace("&amp;","&").replace("&#8217;","’")
            self.content = get_between(x,"<content:encoded><![CDATA[","]]></content:encoded>")[0]
            self.comment_count = int(xml_item_get(x,"slash:comments")[0])
            self.url = xml_item_get(x,"link")[0]
            self.id = int(self.url.split("threads/")[-1].split(".")[-1][:-1])
            self.date_raw = xml_item_get(x,"pubDate")[0]
            self.date = datetime.datetime.strptime(self.date_raw,"%a, %d %b %Y %H:%M:%S %z")
            if category == None:
                category = get_between((x.split("category",1)[1]),"><![CDATA[","]]></category>")[0]
                category_link = get_between(x,'<category domain="','">')[0]
                self.category = HypixelForums.BaseCategory.category(name=category,link=category_link)
            else:
                self.category = category
            self.author = get_between(x,"<dc:creator>","</dc:creator>")[0]
            if self.author.startswith("invalid@example.com (") and self.author.endswith(")"):
                self.author = get_between(self.author.split,"(",")")[0]
            
        def __repr__(self):
            return f'<HypixelForums.Thread title={repr(self.title)} date={repr(self.date)} id={repr(self.id)} link={repr(self.url)}>'
        def __str__(self):
            return self.title
        def __hash__(self):
            return self.id
        def __id__(self):
            return self.id
        def __int__(self):
            return self.id
        def __eq__(self,other):
            if class_name(other) == "HypixelForums.Thread":
                return self.id == other.id
            return False
        def to_dict(self):
            return {
                "title": self.title,
                "content": self.content,
                "url": self.url,
                "date": self.date.timestamp(),
                "id": self.id,
                "category": self.category.id,
                "author": self.author
                }
    def __init__(self):
        txt = requests.get(HypixelForums.rss).text
        self.title = xml_item_get(txt,"title")[0].replace("&amp;","&").replace("&#8217;","’")
        self.description = xml_item_get(txt,"description")[0].replace("&amp;","&")
        self.url = xml_item_get(txt,"link")[0]
        self.threads = []
        self.obj_created = datetime.datetime.utcnow()
        l = xml_item_sep(txt,"item")
        for x in l:
            ar = HypixelForums.Thread(x)
            self.threads.append(ar)
    def refresh(self):
        self.__init__()
    def __contains__(self,other):
        if class_name(other) == "HypixelForums.Thread":
            return other in self.articles
        return False
    def __eq__(self,other):
        if class_name(other) == "HypixelForums":
            return self.id == other.id
        return False
    def __hash__(self):
        tot = 0
        t = self.threads
        for x in t:
            tot += hash(x)
        tot = int(tot/len(t))
        return tot

    class BaseCategory:
        categories = []
        def __init__(self,name=None,link=None,id=None):
            self.name = None
            self.link = None
            if link != None:
                link1 = link.replace("https://hypixel.net/forums/","")
                c_s = link1.split(".")
                if len(c_s) == 1:
                    self.name = c_s[0][:-1].replace("-"," ").title().replace("And","and")
                    if id != None:
                        self.id = id
                    else:
                        self.id = None
                else:
                    self.id = int(c_s[1][:-1])
                    self.name = c_s[0]
                self.link = link
            else:
                if id != None:
                    self.id = id
                    self.link = f"https://hypixel.net/forums/{id}"
                else:
                    self.id = None
                    if name != None:
                        self.link = f"https://hypixel.net/forums/{name}"
            if name != None:
                self.name = name
            if self not in HypixelForums.BaseCategory.categories:
                HypixelForums.BaseCategory.categories.append(self)
        @property
        def rss_link(self):
            l = self.link
            if not l.endswith("/"):
                l += "/"
            l += "-/index.rss"
            return l
        def threads(self):
            txt = requests.get(self.rss_link).text
            title = xml_item_sep(txt,"title")[0]
            if title != self.name:
                self.name = title
                if HypixelForums.load_categories:
                    HypixelForums.BaseCategory._categories_update()
            l = []
            for x in xml_item_sep(txt,"item"):
                t = HypixelForums.Thread(x,category=self)
                l.append(t)
            return l
        def __repr__(self):
            return f'<HypixelForums.BaseCategory name={repr(self.name)} id={repr(self.id)} link={repr(self.link)}>'
        def __str__(self):
            return self.name
        def __eq__(self,other):
            cn = class_name(other)
            if cn == "HypixelForums.BaseCategory":
                a = self.id == other.id
                b = self.name == other.name
                c = self.link == other.link
                return a or b or c
            return False
        def get_category(i):
            c = HypixelForums.BaseCategory.from_id(i)
            if c == None:
                link = f"https://hypixel.net/forums/{i}/"
                txt = requests.get(f"{link}-/index.rss").text
                if "<errors>" in txt:
                    return
                name = xml_item_get(txt,"title")[0]
                c = HypixelForums.BaseCategory.category(name=name,link=link,id=i)
            return c
        def from_id(i):
            for x in HypixelForums.BaseCategory.categories:
                if x.id == i:
                    return x
        def from_name(i):
            for x in HypixelForums.BaseCategory.categories:
                if x.name == i:
                    return x
        def from_url_name(i):
            for x in HypixelForums.BaseCategory.categories:
                if x.name.lower().replace(" ","-") == i.lower().replace(" ","-"):
                    return x
            for x in HypixelForums.BaseCategory.categories:
                if x.name.lower().replace(" ","-").replace("game","[game]") == i.lower().replace(" ","-").replace("game","[game]"):
                    return x
            for x in HypixelForums.BaseCategory.categories:
                if x.name.lower().replace(" ","-").replace("skyblock","[skyblock]") == i.lower().replace(" ","-").replace("skyblock","[skyblock]"):
                    return x
        def from_link(i):
            for x in HypixelForums.BaseCategory.categories:
                if x.link == i:
                    return x
        def category(name=None,link=None,id=None):
            if id != None:
                i = HypixelForums.BaseCategory.from_id(id)
                if i != None:
                    if name != None:
                        i.name = name
                    return i
            if name != None:
                i = HypixelForums.BaseCategory.from_name(name)
                if i != None:
                    if id != None and i.id == None:
                        i.id = id
                    return i
                else:
                    i = HypixelForums.BaseCategory.from_url_name(name)
                    if i != None:
                        i_n = i.name
                        i.name = name
                        if HypixelForums.load_categories:
                            HypixelForums.BaseCategory._categories_update()
                        return i

            if i == None and link != None:
                i = HypixelForums.BaseCategory.from_link(link)
                if i != None:
                    return i
            if HypixelForums.load_categories:
                HypixelForums.BaseCategory._categories_download()
                if id != None:
                    i = HypixelForums.BaseCategory.from_id(id)
                if i == None and link != None:
                    i = HypixelForums.BaseCategory.from_link(link)
                if i != None:
                    return i
            i = HypixelForums.BaseCategory(name=name,link=link,id=id)
            return i
        def _categories_download():
            txt = requests.get('https://hypixel.net/sitemap-1.xml').text

            n_t = []
            for l in txt.splitlines():
                if l.replace("\t","").startswith("<url><loc>"):
                    link = get_between(l,"<url><loc>","</loc></url>")[0]
                    if link.startswith("https://hypixel.net/forums/"):
                        link1 = link.replace("https://hypixel.net/forums/","")
                        c_s = link1.split(".")
                        if len(c_s) == 1:
                            c_s = [c_s[0][:-1],"None/"]
                        c_id = c_s[1][:-1]
                        c_name = c_s[0].replace("-"," ").title().replace("And","and")
                        c_link = link
                        if c_id == "None":
                            if c_name == "Official Hypixel Minecraft Server":
                                c_id = "33"
                            elif c_name == "Prototype":
                                c_id = "122"
                        n_t.append("\t".join((c_id,c_name,c_link)))
                        HypixelForums.BaseCategory(id=c_id,name=c_name,link=c_link)
            n_t = "\n".join(n_t)

            f = open(_category_file,"w+",encoding="utf8")
            f.write(n_t)
            f.close()
        def _categories_update():
            n_t = []
            for c in HypixelForums.BaseCategory.categories:
                n_t.append("\t".join((str(c.id),c.name,c.link)))
            n_t = "\n".join(n_t)

            f = open(_category_file,"w+",encoding="utf8")
            f.write(n_t)
            f.close()

                    
def current_file():
    a = __file__.replace("\\","/")
    a = "/".join(a.split("/")[:-1])
    return a

_category_file = current_file()+"/categories.tsv"

if os.path.exists(_category_file):
    f = open(_category_file,encoding="utf8")
    txt = f.read()
    f.close()
    for x in txt.splitlines():
        _d = {}
        s = x.split("\t")
        d_id = s[0]
        if d_id == "None":
            d_id = None
        else:
            d_id = int(d_id)
        d_name = s[1]
        d_link = s[2]
        c = HypixelForums.BaseCategory.category(name=d_name,id=d_id,link=d_link)
        #print(repr(c))




