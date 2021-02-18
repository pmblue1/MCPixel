import requests
import base64
import json
import datetime
import asyncio
try:
    from PIL import Image
    import PIL
    PIL_IMPORTED = True
except:
    PIL_IMPORTED = False
try:
    import aiohttp
    AIOHTTP_IMPORTED = True
except:
    AIOHTTP_IMPORTED = False
import io
from time import sleep
import traceback

import toolbox

##import mcstatus
##
##server = mcstatus.MinecraftServer.lookup("play.theloungemc.com")
##
##a = server.status()
##print(a)
##print(a.description)
##print(a.latency)
###print(a.favicon)
##print(a.raw)
##print(a.players.online)
##print(a.players.max)
##print("version name:",a.version.name)
##print(a.version.protocol)
##
##
##print(server.port)
##
##print(r)

 
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
def working_paste(i1,i2,cords):
    w1 = cords[0]
    h1 = cords[1]
    w2 = cords[2]
    h2 = cords[3]

    if i2.height-(h2-h1) != 0:
        raise ValueError("Invalid height range")
    if i2.width-(w2-w1) != 0:
        raise ValueError("Invalid width range")

    for h in range(h1,h2):
        for w in range(w1,w2):
            p = i2.getpixel( ( w-w1,h-h1 ) )
            if p != (0,0,0,0):
                i1.putpixel( ( w,h ) , p )
    return i1



class MojangAPI:
    rate_handle = True
    rate_limit_period = 30
    _rate_limit = {"start": datetime.datetime.utcnow(),"sent": 0}
    img_caching = False
    users = []
    def find_user(name):
        for u in MojangAPI.users:
            if u.name.lower() == name.lower():
                return u
        data = [name]
        r = MojangAPI.m_request_post("https://api.mojang.com/profiles/minecraft",json=data).json()
        if r == []:
            return None
        else:
            u = User(r[0]["name"],r[0]["id"])
            MojangAPI.users.append(u)
            return u
    def get_user(uuid):
        for u in MojangAPI.users:
            if u.uuid == uuid:
                return u
        r = MojangAPI.m_request_get(f"https://sessionserver.mojang.com/session/minecraft/profile/{self.uuid}")
        d = r.json()
        if "error" in d:
            return None
        name = d["name"]
        u = User(name,uuid)
        MojangAPI.users.append(u)
        d = json.loads(base64.b64decode(d['properties'][0]["value"]))
        u._skin_url = d["textures"]["SKIN"]["url"]
        if "CAPE" in d["textures"]:
            u._cape_url = d["textures"]["CAPE"]["url"]
        else:
            u._cape_url = False
        u._profile_updated = datetime.datetime.utcnow()
        u.name = d["profileName"]
        return u
    def m_request_get(*args,**kwargs):
        if MojangAPI.rate_handle:
            if (datetime.datetime.utcnow()-MojangAPI._rate_limit["start"]).total_seconds() > MojangAPI.rate_limit_period:
                MojangAPI._rate_limit = {"start": datetime.datetime.utcnow(),"sent": 0}
            elif MojangAPI._rate_limit["sent"] >= MojangAPI.rate_limit_period:
                sec_to_reset = MojangAPI.rate_limit_period-(datetime.datetime.utcnow()-MojangAPI._rate_limit["start"]).total_seconds()
                sleep(sec_to_reset)
        r = requests.get(*args,**kwargs)
        MojangAPI._rate_limit["sent"] += 1
        return r
    def m_request_post(*args,**kwargs):
        if MojangAPI.rate_handle:
            if (datetime.datetime.utcnow()-MojangAPI._rate_limit["start"]).total_seconds() > MojangAPI.rate_limit_period:
                MojangAPI._rate_limit = {"start": datetime.datetime.utcnow(),"sent": 0}
            elif MojangAPI._rate_limit["sent"] >= MojangAPI.rate_limit_period:
                sec_to_reset = MojangAPI.rate_limit_period-(datetime.datetime.utcnow()-MojangAPI._rate_limit["start"]).total_seconds()
                sleep(sec_to_reset)
        r = requests.post(*args,**kwargs)
        MojangAPI._rate_limit["sent"] += 1
        return r



class User:
    def __init__(self,name,uuid,data={}):
        self._name = name
        self.uuid = uuid
        if "skin" not in data:
            self._skin_url = None
        else:
            self._skin_url = data["skin"]
        if "cape" not in data:
            self._cape_url = None
        else:
            self._cape_url = data["cape"]
        self._names = None
        self._names_updated = None
        self._profile_updated = None
        self.updated = datetime.datetime.utcnow()
        if MojangAPI.img_caching:
            self._cape_content = None
            self._skin_content = None
            self._head_content = None
            self._skin_front = None
    def __str__(self):
        return self.name
    @property
    def name(self):
        if self._name == None:
            self._get_profile()
        return self._name
    @property
    def skin_url(self):
        if self._skin_url == None or self._profile_updated < self.updated:
            self._get_profile()
        return self._skin_url
    @property
    def cape_url(self):
        if self._cape_url == None or self._profile_updated < self.updated:
            self._get_profile()
        return self._cape_url
    @property
    def skin(self):
        if MojangAPI.img_caching:
            if self._skin_content == None:
                self._skin_content = requests.get(self.skin_url).content
            return self._skin_content
        return requests.get(self.skin_url).content
    @property
    def cape(self):
        if self.cape_url == False:
            return None
        if MojangAPI.img_caching:
            if self._cape_content == None:
                self._cape_content = requests.get(self.cape_url).content
            return self._cape_content
        return requests.get(self.cape_url).content
    @property
    def name_history(self):
        if self._names == None or self._names_updated < self.updated:
            self._get_name_history()
        return self._names
    def name_at(self,dt):
        nh = reversed(self.name_history)
        for nt in nh:
            if nt.time == None:
                return nt
            if dt > nt.time:
                return nt
    def update(self):
        self.updated = datetime.datetime.utcnow()
    def _get_profile(self):
        r = MojangAPI.m_request_get(f"https://sessionserver.mojang.com/session/minecraft/profile/{self.uuid}")
        d = json.loads(base64.b64decode(r.json()['properties'][0]["value"]))
        self._skin_url = d["textures"]["SKIN"]["url"]
        if "CAPE" in d["textures"]:
            self._cape_url = d["textures"]["CAPE"]["url"]
        else:
            self._cape_url = False
        self._profile_updated = datetime.datetime.utcnow()
        self._name = d["profileName"]
    class NameTime:
        def __init__(self,data):
            self.name = data["name"]
            if "changedToAt" in data:
                self.time = datetime.datetime.fromtimestamp(data["changedToAt"]/1000)
            else:
                self.time = None
        def __str__(self):
            return self.name
        def __repr__(self):
            return f'<User.NameTime name={self.name} time={self.time}>'
            
    def _get_name_history(self):
        r = MojangAPI.m_request_get(f"https://api.mojang.com/user/profiles/{self.uuid}/names")
        d = r.json()
        self._names = []
        for x in d:
            self._names.append(User.NameTime(x))
        self._names_updated = datetime.datetime.utcnow()
    def save_skin(self,file,open_mode="wb+"):
        if str(type(file)) == "<class 'str'>":
            f = open(file,open_mode)
        elif str(type(file)) == "<class '_io.TextIOWrapper'>":
            f = file.buffer
        elif str(type(file)) == "<class '_io.BufferedWriter'>":
            f = file
        else:
            raise ValueError()
        f.write(self.skin)
        f.close()
    def save_cape(self,file,open_mode="wb+"):
        if str(type(file)) == "<class 'str'>":
            f = open(file,open_mode)
        elif str(type(file)) == "<class '_io.TextIOWrapper'>":
            f = file.buffer
        elif str(type(file)) == "<class '_io.BufferedWriter'>":
            f = file
        else:
            raise ValueError()
        f.write(self.cape)
        f.close()
    def get_head(self,overlay=False,as_bytes=False):
        if not PIL_IMPORTED:
            raise ImportError(f"Function unavailable, as PIL was not successfully imported. Please be sure you have PIL installed.")
        b = io.BytesIO(self.skin)
        im = Image.open(b)
        imh = im.crop((8,8,16,16))
        if overlay:
            im_o = im.crop((40,8,48,16))#HEAD OVERLAY
            imh = working_paste(imh,im_o,(0,0,8,8))
        im.close()
        if as_bytes:
            return im_to_bytes(imh)
        else:
            return imh
    def get_front(self,overlay=False,as_bytes=False):
        if not PIL_IMPORTED:
            raise ImportError(f"Function unavailable, as PIL was not successfully imported. Please be sure you have PIL installed.")
        b = io.BytesIO(self.skin)
        i = Image.open(b)

        i1 = i.crop((8,8,16,16))#HEAD
        i2 = i.crop((20,20,28,32))#CHEST/BODY
        i3 = i.crop((44,20,48,38))#LEFT ARM
        i4 = i.crop((36,52,40,64))#RIGHT ARM
        i5 = i.crop((20,52,24,64))#RIGHT LEG
        i6 = i.crop((4,20,8,32))#LEFT LEG

        ni = Image.new("RGBA",(12+i4.width,12+i2.height+i5.height))
        ni.paste(i1,(4,0,12,8))#HEAD
        ni.paste(i2,(4,8,12,8+i2.height))#CHEST/BODY
        ni.paste(i3,(4-i3.width,8,4,8+i3.height))#LEFT ARM
        ni.paste(i4,(12,8,12+i4.width,8+i4.height))#RIGHT ARM
        ni.paste(i5,(12-i5.width,8+i2.height,12,8+i2.height+i5.height))#RIGHT LEG
        ni.paste(i6,(4,8+i2.height,4+i5.width,8+i2.height+i5.height))#LEFT LEG

        if overlay:
            i7 = i.crop((44,36,48,48))#LEFT ARM OVERLAY
            ni = working_paste(ni,i7,(4-i7.width,8,4,8+i7.height))
            
            i8 = i.crop((52,52,56,64))#RIGHT ARM OVERLAY
            ni = working_paste(ni,i8,(12,8,12+i8.width,8+i8.height))
            
            i9 = i.crop((40,8,48,16))#HEAD OVERLAY
            ni = working_paste(ni,i9,(4,0,12,8))
            
            i10 = i.crop((20,36,28,48))#CHEST/BODY OVERLAY
            ni = working_paste(ni,i10,(4,8,12,8+i10.height))
            
            i11 = i.crop((4,52,8,64))#RIGHT LEG OVERLAY
            ni = working_paste(ni,i11,(12-i11.width,8+i11.height,12,8+i2.height+i11.height))
            
            i12 = i.crop((4,36,8,48))#LEFT LEG OVERLAY
            ni = working_paste(ni,i12,(4,8+i12.height,4+i12.width,8+i2.height+i12.height))
        i.close()
        if as_bytes:
            return im_to_bytes(ni)
        else:
            return ni

def ratio_resize(im,ratio):
    return im.resize((im.width*ratio,im.height*ratio),PIL.Image.NEAREST)

m = MojangAPI

u = m.find_user("pmblue")

start = datetime.datetime.utcnow()
u.get_head()
end = datetime.datetime.utcnow()
print(end-start)

start = datetime.datetime.utcnow()
u.get_head()
end = datetime.datetime.utcnow()
print((end-start).total_seconds())
##for _ in range(1):
##    print("\n"+"="*20+"\n")
##    print("\n"+" "*5+"UPDATED"+"\n")
##    u.update()
##    for _ in range(5):
##        print("\n"+"="*20+"\n")
##        print(u.name)
##        print(u.uuid)
##        print(u.skin_url)
##        print(u.cape_url)

u.save_skin("skin.png")
    



bi = io.BytesIO(u.skin)
b = bi.read()#open(bi,"rb")


def im_to_bytes(im,format="png"):
    bi = io.BytesIO()
    im.save(bi,format)
    bi.seek(0)
    return bi.read()
print(len(u.skin))
print(len(b))
#i = PIL.Image.frombuffer("RGB",(64,64),b)#Image.open("skin.png")
i = Image.open(bi)
print(len(i.tobytes()))
bi = io.BytesIO()
i.save(bi,"png")
bi.seek(0)
print(len(bi.read()))
if False:
    for x in range(0,64,2):
        i.putpixel((7,x),(10,10,256,100))
        i.putpixel((7,x+1),(256,256,10,256))
        
        i.putpixel((40,x),(10,10,256,100))
        i.putpixel((40,x+1),(256,256,10,256))
        
        i.putpixel((x,15),(10,10,256,100))
        i.putpixel((x+1,15),(256,256,10,256))
        
        i.putpixel((x,40),(10,10,256,100))
        i.putpixel((x+1,40),(256,256,10,256))

print(len(i.tobytes()))
i = i.resize((640,640),PIL.Image.NEAREST)
i.save("skin2.png")
i.save("skin.png")
tb = im_to_bytes(i)#i.tobytes()
print(len(tb))
f = open("skin1.png","wb+")
f.write(tb)
f.close()
#i3.show()
print(u.uuid)
print(u.name)

ni = u.get_head(overlay=True)

ni = ni.resize((ni.width*8,ni.height*8),PIL.Image.NEAREST)

ni.save("new_skin.png")

#ni.show()




_gametype_str = """2	QUAKECRAFT	Quake	Quake
3	WALLS	Walls	Walls
4	PAINTBALL	Paintball	Paintball
5	SURVIVAL_GAMES	HungerGames	Blitz Survival Games
6	TNTGAMES	TNTGames	TNT Games
7	VAMPIREZ	VampireZ	VampireZ
13	WALLS3	Walls3	Mega Walls
14	ARCADE	Arcade	Arcade
17	ARENA	Arena	Arena
20	UHC	UHC	UHC Champions
21	MCGO	MCGO	Cops and Crims
23	BATTLEGROUND	Battleground	Warlords
24	SUPER_SMASH	SuperSmash	Smash Heroes
25	GINGERBREAD	GingerBread	Turbo Kart Racers
26	HOUSING	Housing	Housing
51	SKYWARS	SkyWars	SkyWars
52	TRUE_COMBAT	TrueCombat	Crazy Walls
54	SPEED_UHC	SpeedUHC	Speed UHC
55	SKYCLASH	SkyClash	SkyClash
56	LEGACY	Legacy	Classic Games
57	PROTOTYPE	Prototype	Prototype
58	BEDWARS	Bedwars	Bed Wars
59	MURDER_MYSTERY	MurderMystery	Murder Mystery
60	BUILD_BATTLE	BuildBattle	Build Battle
61	DUELS	Duels	Duels
63	SKYBLOCK	SkyBlock	SkyBlock
64	PIT	Pit	Pit"""
class GameType:
    def __init__(self,d):
        self.id = d["id"]
        self.type = d["type"]
        self.database = d["database"]
        self.clean = d["clean"]
        self.dict = d
    def __str__(self):
        return self.clean
    def __repr__(self):
        return f'<GameType id={repr(self.id)} type={repr(self.type)} database={repr(self.database)} clean={repr(self.clean)}>'
    def __getitem__(self,key):
        return self.dict[key]
    def from_id(i):
        for x in GameType.games:
            if x["id"] == i:
                return x
    def from_type(i):
        for x in GameType.games:
            if x["type"].lower() == i.lower():
                return x
    def from_database(i):
        for x in GameType.games:
            if x["database"].lower() == i.lower():
                return x
    def from_clean(i):
        for x in GameType.games:
            if x["clean"].lower() == i.lower():
                return x
    def from_str(i):
        r = GameType.from_type(i)
        if r == None:
            r = GameType.from_database(i)
        if r == None:
            r = GameType.from_clean(i)
        return r
    games = []
for x in _gametype_str.splitlines():
    _d = {}
    s = x.split("\t")
    _d["id"] = int(s[0])
    _d["type"] = s[1]
    _d["database"] = s[2]
    _d["clean"] = s[3]
    GameType.games.append(GameType(_d))

def hypixel_timestamp(t):
    return datetime.datetime.utcfromtimestamp(int(t)/1000)
def hypixel_level(exp):
    return (((2 * exp) + 30625)**(1/2) / 50) - 2.5
def hypixel_guild_level(exp):
    EXP_NEEDED = [
    100000,
    150000,
    250000,
    500000,
    750000,
    1000000,
    1250000,
    1500000,
    2000000,
    2500000,
    2500000,
    2500000,
    2500000,
    2500000,
    3000000,]

    level = 0

    for i in range(0, 1000):
        need = 0
        if i >= len(EXP_NEEDED):
            need = EXP_NEEDED[len(EXP_NEEDED) - 1]
        else:
            need = EXP_NEEDED[i]
        i += 1

        if (exp - need) < 0:
            return round((level + (exp / need)) * 100) / 100
        level += 1
        exp -= need

    return 0


class Achievements:
    class OneTime:
        def __init__(self,data,key,type=None):
            self.key = key
            self.full_key = type+"_"+key
            self.type = type
            self.name = data["name"]
            self.description = data["description"]
            self.is_tiered = False
            if "legacy" in data:
                self.legacy = data["legacy"]
            else:
                self.legacy = False
            if "gamePercentUnlocked" in data:#Users who have played at least 1 game in category
                self.players_unlocked = data["gamePercentUnlocked"]
            else:
                self.players_unlocked = None
            if "globalPercentUnlocked" in data:#All users
                self.global_unlocked = data["globalPercentUnlocked"]
            else:
                self.global_unlocked = None
            if "points" in data:
                self.points = data["points"]
            else:
                self.points = None
    class Tiered:
        def __init__(self,data,key,type=None):
            self.key = key
            self.full_key = type+"_"+key
            self.type = type
            self.name = data["name"]
            self.description = data["description"]
            self.tiers = []
            self.points = 0
            self.max_tier = 0
            for x in data["tiers"]:
                t = Achievements.Tier(x,self)
                self.tiers.append(t)
                self.points += x["points"]
                self.max_tier += 1
            self.is_tiered = True
            if "legacy" in data:
                self.legacy = data["legacy"]
            else:
                self.legacy = False
        def __len__(self):
            return len(self.tiers)
        def get_tier(self,tier_number):
            for x in self.tiers:
                if x.tier == tier_number:
                    return x
    class GuildTiered(Tiered):
        def __init__(self,data,key):
            self.key = key
            self.full_key = key
            self.type = None
            self.name = data["name"]
            self.description = data["description"]
            self.tiers = []
            self.max_tier = 0
            for x in data["tiers"]:
                t = Achievements.Tier(x,self)
                self.tiers.append(t)
                self.max_tier += 1
            self.is_tiered = True
    class Tier:
        def __init__(self,data,tiered):
            self.tier = data["tier"]
            self.amount = data["amount"]
            self.description = tiered.description.replace("%s",str(self.amount))
            if "points" in data:
                self.points = data["points"]
            else:
                self.points = None
        def __repr__(self):
            return f'<Tier tier={repr(self.tier)} amount={repr(self.amount)} points={repr(self.points)}>'
    class Type:
        def __init__(self,atype,a_obj):
            self.type = atype
            self.a_obj = a_obj
        def one_time(self,legacy=None):
            l = []
            for a in self.a_obj.one_time(legacy):
                if self.type == a.type:
                    l.append(a)
            return l
        def tiered(self,legacy=None):
            l = []
            for a in self.a_obj.tiered(legacy):
                if self.type == a.type:
                    l.append(a)
            return l
        def all(self,legacy=None):
            l = []
            for a in self.a_obj.all_iter(legacy):
                if self.type == a.type:
                    l.append(a)
            return l
        def points(self,legacy=None):
            p = 0
            for a in self.all(legacy):
                p += a.points
            return p
        def __eq__(self,other):
            cn = class_name(other)
            if cn == "str":
                return self.type == other
            elif cn == "Achievements.Type":
                return self.type == other.type
            return False
    class ContextAchievement:
        def __init__(self,a,amt=None):
            self.achievement = a
            self.current_amount = amt
            if a.is_tiered:
                self.current_tier = 0
                for x in a.tiers:
                    if x.amount <= amt:
                        self.current_tier = x.tier
                        break
        def __repr__(self):
            return f'<ContextAchievement is_tiered={self.achievement.is_tiered} type={self.achievement.type} full_key={self.achievement.full_key}>'
                
    def _player_load(self,hr):
        if not self.loaded:
            self.load()
        d = hr.data["player"]
        dt = d["achievements"]
        dot = d["achievementsOneTime"]
        l = []
        for key,amt in iter_dict(dt):
            a = self._get_achievement(key)
            if a == None:
                continue
            ca = Achievements.ContextAchievement(a,amt)
            l.append(ca)
        for key in dot:
            a = self._get_achievement(key)
            if a == None:
                continue
            ca = Achievements.ContextAchievement(a)
            l.append(ca)
        return l
    def _guild_load(self,hr):
        if not self.loaded:
            self.load()
        d = hr.data["guild"]
        dt = d["achievements"]
        l = []
        for key,amt in iter_dict(dt):
            a = self._get_achievement(key)
            ca = Achievements.ContextAchievement(a,amt)
            l.append(ca)
        return l
    def __init__(self):
        self.loaded = False
    def load(self):
        self.loaded = True
        r = requests.get("https://api.hypixel.net/resources/guilds/achievements")
        d = r.json()
        self.guild_last_updated = hypixel_timestamp(d["lastUpdated"]/1000)
        self.guild_achievements = []
        for x,y in iter_dict(d["tiered"]):
            a = Achievements.GuildTiered(y,x)
            self.guild_achievements.append(a)
        r = requests.get("https://api.hypixel.net/resources/achievements")
        d = r.json()
        self.last_updated = hypixel_timestamp(d["lastUpdated"]/1000)
        self.achievements = []
        self.types = []
        for atype,type_dict in iter_dict(d["achievements"]):
            for x,y in iter_dict(type_dict["one_time"]):
                a = Achievements.OneTime(y,x,atype)
                self.achievements.append(a)
            for x,y in iter_dict(type_dict["tiered"]):
                a = Achievements.Tiered(y,x,atype)
                self.achievements.append(a)
            t = Achievements.Type(atype,self)
            self.types.append(t)
    def all_iter(self,legacy=None):
        for a in self.achievements:
            if legacy == None or legacy == a.legacy:
                yield a
    def one_time(self,legacy=None):
        l = []
        for a in self.achievements:
            if not a.is_tiered:
                if legacy == None or legacy == a.legacy:
                    l.append(a)
        return l
    def tiered(self,legacy=None):
        l = []
        for a in self.achievements:
            if a.is_tiered:
                if legacy == None or legacy == a.legacy:
                    l.append(a)
        return l
    def get_type(self,atype):
        for x in self.types:
            if x == atype:
                return x
    def _get_achievement(self,key):
        def process(i):
            return i.lower().replace("_","").replace(" ","")
        kl = process(key)
        for a in self.achievements:
            al = process(a.full_key)
            if kl == al:
                return a
        for a in self.guild_achievements:
            al = process(a.full_key)
            if kl == al:
                return a






class HypixelGuild:
    class Member:
        class ExpHistory:
            def __init__(self,time_key,value):
                tk_s = time_key.split("-")
                year = int(tk_s[0])
                month = int(tk_s[1])
                day = int(tk_s[2])
                self.date = datetime.date(year,month,day)
                self.exp = value
        def __init__(self,data,guild):
            api = guild.api
            self.guild = guild
            self.joined = hypixel_timestamp(data["joined"])
            self.uuid = data["uuid"]
            self.user = api._get_user(self.uuid)
            self.rank_name = data["rank"]
            if "quest_participation" in data:
                self.quest_participation = data["quest_participation"]
            else:
                self.quest_participation = 0
            if "mutedTill" in data:
                mt = data["mutedTill"]
                mt_dt = hypixel_timestamp(mt)
                if mt_dt < datetime.datetime.utcnow():
                    self.muted_until = None
                else:
                    self.muted_until = mt_dt
            else:
                self.muted_until = None
            self.exp_history = []
            if "expHistory" in data:
                for key,value in iter_dict(data["expHistory"]):
                    eh = HypixelGuild.Member.ExpHistory(key,value)
                    self.exp_history.append(eh)
            self.rank = guild.member_rank(self)
            self.owner = False
            if self.rank == None:
                print(self.user.name,self.rank_name)
            else:
                if self.rank.owner_role:
                    print("OWNER:",self.user.name,self.rank_name)
                    self.owner = True
                    
                    


    class Rank:
        class GuildMaster:
            def __init__(self,guild):
                self.guild = guild
                self.name = "Guild Master"
                self.default = False
                self.tag = None
                self.created = guild.created
                self.priority = None
                self.owner_role = True
                self._members = None
            @property
            def members(self):
                if self._members == None:
                    self._members = []
                    for m in self.guild.members:
                        if m.rank == self:
                            self._members.append(m)
                return self._members
            def is_rank(self,member):
                if member.rank_name == "GUILDMASTER" or member.rank_name == "Guild Master":
                    return True
                return False
            def __gt__(self,other):
                cn = class_name(other)
                if cn == "HypixelGuild.Rank":
                    return True
                elif cn == "HypixelGuild.Rank.GuildMaster":
                    return False
            def __eq__(self,other):
                cn = class_name(other)
                if cn == "HypixelGuild.Rank":
                    if self.guild == other.guild:
                        if self.name == other.name:
                            return True
                    return False
                elif cn == "HypixelGuild.Rank.GuildMaster":
                    if self.guild == other.guild:
                        return True
                    return False
                return False
            def __repr__(self):
                return f'<HypixelGuild.Rank.GuildMaster name={self.name} default={self.default} tag={self.tag} priority={self.priority}>'
        def __init__(self,data,guild):
            self.guild = guild
            self.name = data["name"]
            self.default = data["default"]
            self.tag = data["tag"]
            self.created = hypixel_timestamp(data["created"])
            self.priority = data["priority"]
            self.owner_role = False
            self._members = None
        @property
        def members(self):
            if self._members == None:
                self._members = []
                for m in self.guild.members:
                    if m.rank == self:
                        self._members.append(m)
            return self._members
        def is_rank(self,member):
            if member.rank_name.lower() == self.name.lower():
                return True
            return False
        def __gt__(self,other):
            cn = class_name(other)
            if cn == "HypixelGuild.Rank":
                return self.priority > other.priority
            elif cn == "HypixelGuild.Rank.GuildMaster":
                return False
        def __eq__(self,other):
            cn = class_name(other)
            if cn == "HypixelGuild.Rank":
                if self.guild == other.guild:
                    if self.name == other.name:
                        return True
                return False
            return False
        def __repr__(self):
            return f'<HypixelGuild.Rank name={self.name} default={self.default} tag={self.tag} priority={self.priority}>'
    def __init__(self,hr):
        self.api = hr.api
        self.cache = HypixelAPI.Cache(self.api)
        self._load(hr)
        self.cache["guild"] = hr
    def _load(self,hr):
        hr.inherit(self)
        data = hr.data
        gd = data["guild"]
        self.id = gd["_id"]
        if "legacyRanking" in gd:
            self.legacy_ranking = gd["legacyRanking"]
        else:
            self.legacy_ranking = None
        self.name = gd["name"]
        self.tag = gd["tag"]
        self.created = hypixel_timestamp(gd["created"])
        
        self.exp = gd["exp"]
        self.level = hypixel_guild_level(gd["exp"])
        self.exp_by_game = gd["guildExpByGameType"]
        if "tagColor" in gd:
            self.tag_color = gd["tagColor"]
        else:
            self.tag_color = None
        if "chatMute" in data:
            cm = data["chatMute"]
            cm_dt = hypixel_timestamp(mt)
            if cm_dt < datetime.datetime.utcnow():
                self.muted_until = None
            else:
                self.muted_until = cm_dt
        else:
            self.muted_until = None
        if "preferredGames" in gd:
            self.preferred_games = gd["preferredGames"]
        else:
            self.preferred_games = []
        if "joinable" in gd:
            self.joinable = gd["joinable"]
        else:
            self.joinable = True
        if "publiclyListed" in gd:
            self.publicly_listed = gd["publiclyListed"]
        else:
            self.publicly_listed = True
        if "coins" in gd:
            self.coins = gd["coins"]
        else:
            self.coins = None
        if "coinsEver" in gd:
            self.coins_ever = gd["coinsEver"]
        else:
            self.coins_ever = None
        self.ranks = []
        self.default = None
        if "ranks" in gd:
            for x in gd["ranks"]:
                r = HypixelGuild.Rank(x,self)
                self.ranks.append(r)
                if r.default:
                    self.default = r
        else:
            x = {
                "name": "MEMBER",
                "priority": 1,
                "default": True,
                "tag": None,
                "created": gd["created"]
                }
            r = HypixelGuild.Rank(x,self)
            self.default = r
            self.ranks.append(r)
            x = {
                "name": "OFFICER",
                "priority": 2,
                "default": False,
                "tag": None,
                "created": gd["created"]
                }
            r = HypixelGuild.Rank(x,self)
            self.ranks.append(r)
        r = HypixelGuild.Rank.GuildMaster(self)
        self.ranks.append(r)
        self.ranks.sort()
        self.members = []
        for x in gd["members"]:
            m = HypixelGuild.Member(x,self)
            self.members.append(m)
    def _update(self):
        params = {
            "id": self.id
            }
        hr = self.api.request_get('https://api.hypixel.net/guild',params=params)
        self._load(hr)
        self.cache["guild"] = hr
    def achievements(self):
        a_obj = self.api.achievements
        if not self.cache.is_updated("guild"):
            self._update()
        hr = self.cache["guild"]
        ua = a_obj._guild_load(hr)
        return ua
    def get_member(self,uuid):
        for m in self.members:
            if m.uuid == uuid:
                return m   
    def get_rank(self,name):
        for r in self.ranks:
            if r.name.lower() == name:
                return r        
    def member_rank(self,member):
        for r in self.ranks:
            if r.is_rank(member):
                return r
    def __eq__(self,other):
        cn = class_name(other)
        if cn == "HypixelGuild":
            if self.id == other.id:
                return True
        return False



class HypixelUser(User):
    class Status:
        def __init__(self,hr):
            hr.inherit(self)
            s = hr.data["session"]
            if s["online"]:
                self.online = True
                if "game" in s:
                    self.game_name = s["game"]
                else:
                    self.game_name = None
                if "mode" in s:
                    self.mode = s["mode"]
                else:
                    self.mode = None
                if "map" in s:
                    self.map = s["map"]
                else:
                    self.map = None
            else:
                self.online = False
                self.game_name = None
                self.mode = None
                self.map = None
        def __repr__(self):
            if self.online:
                return f'<Status online=True game_name={repr(self.game_name)} mode={repr(self.mode)} map={repr(self.map)}>'
            else:
                return f'<Status online=False>'


    class Friend:
        def __init__(self,data,user):
            api = user.api
            started = data["started"]
            s = data["uuidSender"]
            r = data["uuidReceiver"]
            if user.uuid == s:
                self.from_user = True
                self.user = api._get_user(r)
            else:
                self.from_user = False
                self.user = api._get_user(s)
            self.started = hypixel_timestamp(started)
        @property
        def duration(self):
            return datetime.datetime.utcnow() - self.started
    class RecentGame:
        def __init__(self,data):
            self.started = hypixel_timestamp(data["date"])
            self.game_name = data["gameType"]
            if "mode" in data:
                self.mode = data["mode"]
            else:
                self.mode = None
            if "map" in data:
                self.map = data["map"]
            else:
                self.map = None
            if "ended" in data:
                self.ended = hypixel_timestamp(data["ended"])
            else:
                self.ended = None
        @property
        def duration(self):
            if self.ended == None:
                return datetime.datetime.utcnow() - self.started
            else:
                return self.ended - self.started
            
    def __init__(self,uuid,api,data={}):
        User.__init__(self,None,uuid,data)
        self.api = api
        self.cache = HypixelAPI.Cache(api)
        self.loaded = False
    def __del__(self):
        del self.cache
        self.api._users.remove(self)
    def _player_load(self,r):
        d = r.data["player"]
        self.karma = d["karma"]
        self.first_login = hypixel_timestamp(d["firstLogin"])
        self.latest_login = hypixel_timestamp(d["lastLogin"])
        self.last_logout = hypixel_timestamp(d["lastLogout"])
        if "timePlaying" in d:
            self.time_played = datetime.timedelta(minutes=d["timePlaying"])
        else:
            self.time_played = None
        self.exp = d["networkExp"]
        if "achievement_points" in d:
            self.achievement_points = d["achievementPoints"]
        else:
            self.achievement_points = 0
        self.level = hypixel_level(self.exp)
        self.loaded = True
    def _player(self):
        params = {
            "uuid": self.uuid
            }
        try:
            r = self.api.request_get("https://api.hypixel.net/player",params=params)
        except HypixelException.InvalidUUID:
            del self
            return
        f = open("player.json","w+")
        json.dump(r.data,f,indent=2)
        f.close()
        self.cache["player"] = r
        self._player_load(r)
    def status(self):
        if not self.cache.is_updated("status"):
            params = {
                "uuid": self.uuid
                }
            r = self.api.request_get("https://api.hypixel.net/status",params=params)
            s = HypixelUser.Status(r)
            self.cache["status"] = s
        return self.cache["status"]
    def friends(self):
        if not self.cache.is_updated("friends"):
            params = {
                "uuid": self.uuid
                }
            r = self.api.request_get("https://api.hypixel.net/friends",params=params)
            l = []
            for x in r.data["records"]:
                f = HypixelUser.Friend(x)
                l.append(f)
            self.cache["friends"] = l
        return self.cache["friends"]
    def recent_games(self):
        if not self.cache.is_updated("recent_games"):
            params = {
                "uuid": self.uuid
                }
            r = self.api.request_get("https://api.hypixel.net/recentGames",params=params)
            l = []
            for x in r.data["games"]:
                f = HypixelUser.RecentGame(x)
                l.append(f)
            self.cache["recent_games"] = l
        return self.cache["recent_games"]
    def achievements(self):
        a_obj = self.api.achievements
        if not self.cache.is_updated("player"):
            self._player()
        hr = self.cache["player"]
        ua = a_obj._player_load(hr)
        return ua
    def __eq__(self,other):
        cn = class_name(other)
        if cn == "HypixelUser":
            return self.uuid == other.uuid
        elif cn == "str":
            return self.uuid == other
        return False
        
    
        


class HypixelException:
    class InvalidKey(Exception):
        def __init__(self,hr):
            key = hr.key
            Exception.__init__(self,f'The following key is not valid: "{key}"')
    class ExceededRateLimit(Exception):
        def __init__(self):
            Exception.__init__(self,f'Rate limit was exceeded.')
    class InvalidUUID(Exception):
        def __init__(self):
            Exception.__init__(self,f'Invalid UUID exception returned.')
    class InvalidGuildID(Exception):
        def __init__(self):
            Exception.__init__(self,f'Invalid Guild ID exception returned.')
    class MissingParams(Exception):
        def __init__(self,hr):
            cause = hr.data["cause"]
            missing = cause.split("[",1)[1].split("]",1)[0]
            Exception.__init__(self,f'The following parameter is missing from querystring: {missing}')
    class APIError(Exception):
        def __init__(self,hr):
            cause = hr.data["cause"]
            Exception.__init__(self,cause)

class HypixelAPIKey:
    def __init__(self,key,api):
        self.api = api
        self._key = key
        self._checked = False
        self._limit = None
        self._owner_uuid = None
        self._last_request = None
    def __str__(self):
        return self.get()
    def get(self):
        if not self._checked:
            self._info()
        return self._key
    def _info(self):
        r = self.api.request_get(f'https://api.hypixel.net/key',params={},key=self)
        j = r.data
        if j["success"]:
            self._owner_uuid = j["record"]["owner"]
            self._limit = j["record"]["limit"]
            self._checked = True
            return j
        else:
            raise HypixelException.InvalidKey(self._key)
    def is_available(self):
        if self._last_request == None:
            return True
        rl = self._last_request.rate_limit
        if rl.remaining == 0:
            dt = datetime.datetime.utcnow()
            reset_time = rl.time+datetime.timedelta(seconds=rl.reset)
            if reset_time > dt:
                return False
        return True
    @property
    def key(self):
        if not self._checked:
            self._info()
        return self._key
    @property
    def owner_minecraft(self):
        if self._owner_uuid == None:
            self._info()
        return User(None,self.owner_uuid)
    @property
    def owner_uuid(self):
        if self._owner_uuid == None:
            self._info()
        return self._owner_uuid
    @property
    def limit(self):
        if self._limit == None:
            self._info()
        return self._limit
    def total(self):
        return self._info()["record"]["totalQueries"]
    def __str__(self):
        return self.key
    def __eq__(self,other):
        cn = class_name(other)
        if cn == 'str':
            return self.key == other
        elif cn == 'HypixelAPIKey':
            return self.key == other.key
        return False
        

            
class HypixelAuth:
    def __init__(self,data,api):
        self.api = api
        cn = class_name(data)
        if cn in "str":
            self.keys = [HypixelAPIKey(data,api)]
        elif cn in "list":
            ind = -1
            self.keys = []
            for x in data:
                ind += 1
                x_cn = class_name(x)
                if x_cn != "str":
                    raise TypeError(f"Inside given key list, item at index {ind} was a {x_cn} type, not a str.")
                self.keys.append(HypixelAPIKey(x,api))
            if ind == -1:
                raise ValueError(f"List provided is empty.")
        elif cn in "tuple":
            ind = -1
            self.keys = []
            for x in data:
                ind += 1
                x_cn = class_name(x)
                if x_cn != "str":
                    raise TypeError(f"Inside given key tuple, item at index {ind} was a {x_cn} type, not a str.")
                self.keys.append(HypixelAPIKey(x,api))
            if ind == -1:
                raise ValueError(f"tuple provided is empty.")
        else:
            raise TypeError(f"{cn} type was provided for keys, but is invalid. Must be str,list, or tuple")
    def __iter__(self):
        self._iterable = iter(self.keys)
        return self
    def __next__(self):
        return next(self._iterable)
    def _next_key(self):
        k = self.keys.pop(0)
        self.keys.append(k)
        return k
    def next_key(self):
        k = None
        for k in self:
            if k.is_available():
                break
        return k
    def get_key(self,key):
        for x in self.keys:
            if key == x:
                return x
    def __getitem__(self,key):
        for x in self.keys:
            if key == x:
                return x


def HypixelRateHandle(rl):
    if rl.remaining <= 0:
        dt = datetime.datetime.utcnow()
        reset_time = rl.time+datetime.timedelta(seconds=rl.reset)
        if reset_time > dt:
            until_reset = (reset_time-dt).total_seconds()
            sleep(until_reset+1)

class HypixelAPI:
    class WatchDog:
        def __init__(self,hr):
            hr.inherit(self)
            self.time = hr.time
            
            self.wd_last_minute = hr.data["watchdog_lastMinute"]
            self.wd_last_day = hr.data["watchdog_rollingDaily"]
            self.wd_total = hr.data["watchdog_total"]
            
            self.staff_last_day = hr.data["staff_rollingDaily"]
            self.staff_total = hr.data["staff_total"]

            self.last_day = self.wd_last_day+self.staff_last_day
            self.total = self.wd_total+self.staff_total

    class Cache:
        def __init__(self,api):
            self.api = api
            self._updates = {}
            self._items = {}
        def __getitem__(self,key):
            return self._items[key]
        def __setitem__(self,key,value):
            self._items[key] = value
            self._updates[key] = datetime.datetime.utcnow()
        def __delitem__(self,key):
            del self._updates[key]
        def is_updated(self,key):
            if not self.api.adv_caching:
                return False
            if key not in self._updates:
                return False
            last_updated = self._updates[key]
            dt = datetime.datetime.utcnow()
            update_after = self.api.cached_update_after
            if (dt-last_updated).total_seconds() > update_after:
                return False
            return True
        def __iter__(self):
            self._iterable = iter(self._items.values())
            return self
        def __next__(self):
            return next(self._iterable)
        def __contains__(self,other):
            for x in self._items:
                if x == other:
                    return True
            return False
        def __del__(self):
            self.clear()
        def clear(self):
            del self._updates
            del self._items
            
            self._updates = {}
            self._items = {}
    
            
        
    def __init__(self,auth,rate_handle={"mode": "before","call": HypixelRateHandle,"retry": True},adv_caching=True,cached_update_after=600):
        self.auth = HypixelAuth(auth,self)
        self.adv_caching = True
        self._users = []
        self._guilds = []
        self._rate_before = False
        self._rate_retry = False
        self._last_request = None
        self.cache = HypixelAPI.Cache(self)
        self.cached_update_after = cached_update_after
        self.achievements = Achievements()
        cn = class_name(rate_handle)
        if cn == "dict":
            if "mode" not in rate_handle:
                raise ValueError(f"'mode' not defined in rate_handle dict.")
            else:
                rhm = rate_handle["mode"]
                if rhm == "before":
                    self._rate_before = True
                elif rhm == "after":
                    self._rate_before = False
                else:
                    raise ValueError(f"'mode' must be either 'before' or 'after', but is {rhm}")
            if "call" not in rate_handle:
                raise ValueError(f"'call' not defined in rate_handle dict.")
            else:
                rhc = rate_handle["call"]
                if not callable(rhc):
                    raise ValueError(f"'call' key must be callable.")
                self._rate_handle = rhc
            if "retry" not in rate_handle:
                raise ValueError(f"'retry' not defined in rate_handle dict.")
            else:
                rhr = rate_handle["retry"]
                cn = class_name(rhr)
                if cn != "bool":
                    raise TypeError(f"'retry' key must be bool, but is a '{cn}'.")
                self._rate_retry = rhr
        elif callable(rate_handle):
            self._rate_handle = rate_handle
        else:
            raise ValueError(f'rate_handle is not callable or a dict. Is {cn} type.')
    def response_error_check(self,hr):
        if not hr.data["success"]:
            cause = hr.data["cause"]
            if cause == "Invalid API key":
                raise HypixelException.InvalidKey(hr)
            elif cause == "Malformed UUID":
                raise HypixelException.InvalidUUID()
            elif cause == "Malformed guild ID":
                raise HypixelException.InvalidGuildID()
            elif cause.startswith("Missing one or more fields"):
                raise HypixelException.MissingParams(hr)
            else:
                raise HypixelException.APIError(hr)
    def request_get(self,*args,**kwargs):
        if "params" in kwargs:
            params = kwargs["params"]
            del kwargs["params"]
        else:
            params = {}
        if "key" in kwargs:
            key = kwargs["key"]
            del kwargs["key"]
            if key != None:
                params["key"] = key._key
        else:
            key = self.auth.next_key()
            params["key"] = str(key)
            
        if self._rate_before:
            if key._last_request != None:
                self._rate_handle(key._last_request.rate_limit)
        
        r = requests.get(*args,params=params,**kwargs)
        if r.status_code == 429:
            if self._rate_retry:
                if "Retry-After" in r.headers:
                    if str(r.headers["Retry-After"]) == "0":
                        sleep(1)
                        s = False
                    else:
                        s = True
                else:
                    s = True
                if s:
                    hrl = HypixelResponse.RateLimit(r,key)
                    sleep(hrl.reset+1)
                r = requests.get(*args,params=params,**kwargs)
            else:
                raise HypixelException.ExceededRateLimit()
        hr = HypixelResponse(r,key)
        if r.status_code == 429:
            raise HypixelException.ExceededRateLimit()
        self.response_error_check(hr)
        if not self._rate_before:
            self._rate_handle(hr.rate_limit)
        self._last_request = hr
        return hr
    async def async_request_get(self,*args,**kwargs):
        if "params" in kwargs:
            params = kwargs["params"]
            del kwargs["params"]
        else:
            params = {}
        if "key" in kwargs:
            key = kwargs["key"]
            del kwargs["key"]
            params["key"] = key._key
        else:
            key = self.auth.next_key()
            params["key"] = str(key)
            
        if self._rate_before:
            if key._last_request != None:
                if asyncio.iscoroutinefunction(self._rate_handle):
                    await self._rate_handle(key._last_request.rate_limit)
                else:
                    self._rate_handle(key._last_request.rate_limit)
        
        r = await AiohttpResponse.get(*args,params=params,**kwargs)
        requests.Request()
        if r.status_code == 429:
            if self._rate_retry:
                if "Retry-After" in r.headers:
                    if str(r.headers["Retry-After"]) == "0":
                        sleep(1)
                        s = False
                    else:
                        s = True
                else:
                    s = True
                if s:
                    hrl = HypixelResponse.RateLimit(r,key)
                    sleep(hrl.reset+1)
                r = requests.get(*args,params=params,**kwargs)
            else:
                raise HypixelException.ExceededRateLimit()
        hr = HypixelResponse(r,key)
        if r.status_code == 429:
            raise HypixelException.ExceededRateLimit()
        self.response_error_check(hr)
        if not self._rate_before:
            self._rate_handle(hr.rate_limit)
        self._last_request = hr
        return hr
    def watch_dog_stats(self):
        if not self.cache.is_updated("watch_dog_stats"):
            hr = self.request_get("https://api.hypixel.net/watchdogstats")
            self.cache["watch_dog_stats"] = HypixelAPI.WatchDog(hr)
        return self.cache["watch_dog_stats"]
    def from_user(self,user):
        return self._get_user(user.uuid)
    def _get_user(self,uuid):
        for x in self._users:
            if uuid == x.uuid:
                return x
        u = HypixelUser(uuid,self)
        self._users.append(u)
        return u
    def get_user(self,uuid):
        for x in self._users:
            if uuid == x.uuid:
                return x
        params = {
            "uuid": uuid
            }
        try:
            r = self.api.request_get("https://api.hypixel.net/player",params=params)
        except HypixelException.InvalidUUID:
            return None
        u = HypixelUser(uuid,self)
        self._users.append(u)
        u.cache["player"] = r
        u._player_load(r)
        return u
    def _get_guild(self,i):
        for x in self._guilds:
            if i == x.id:
                return x
    def get_guild(self,i):
        for x in self._guilds:
            if i == x.id:
                return x
        params = {
            "id": i
            }
        try:
            r = self.api.request_get("https://api.hypixel.net/guild",params=params)
        except HypixelException.InvalidGuildID:
            return None
        g = HypixelGuild(r,self)
        self._guilds.append(g)
        return g


class HypixelResponse:
    class RateLimit:
        def __init__(self,r,key,time=None):
            self.remaining = int(r.headers["ratelimit-remaining"])
            self.limit = int(r.headers["ratelimit-limit"])
            self.reset = int(r.headers["ratelimit-reset"])
            if time == None:
                self.time = datetime.datetime.utcnow()
            else:
                self.time = time
            self.key = key
        def __repr__(self):
            return f"<RateLimit limit={self.limit} remaining={self.remaining} reset={self.reset}>"
    def __init__(self,r,key):
        self.time = datetime.datetime.utcnow()
        if "ratelimit-reset" in r.headers:
            self.rate_limit = HypixelResponse.RateLimit(r,key,self.time)
        else:
            self.rate_limit = None
        try:
            self.data = r.json()
        except:
            self.data = None
        self.response = r
        self.key = key
        self.api = key.api
        key._last_request = self
    def inherit(self,obj):
        obj.rate_limit = self.rate_limit
        obj.time = self.time
        obj.response = self
            
def hypixel_friends(uuid,key="*****************"):
    r = requests.get(f"https://api.hypixel.net/friends?key={key}&uuid={uuid}")
    return HypixelResponse(r)

class HypixelFriends:
    def __init__(self):
        self.keys = [
            "*****************",
            "*****************"
            ]
    def friends(self,uuid):
        return hypixel_friends(uuid,self.get_key())
    def get_key(self):
        k = self.keys.pop(0)
        self.keys.append(k)
        return k
##
##import toolbox
##
##hf = HypixelFriends()
##
##start = datetime.datetime.utcnow()
##users = {}
##max_depth = 10
##ng = 10
##prev_total = 0
##prev_amt = 0
##depth_dict = {}
##depth_amt1 = 0
##def hypixel_save_friends(uuid,depth=0):
##    global start
##    global users
##    global max_depth
##    global ng
##    global depth_dict
##    global prev_total
##    global prev_amt
##    global hf
##    global depth_amt1
##    depth += 1
##    if depth >= max_depth:
##        return
##    r = hf.friends(uuid)
##    if depth == 1:
##        depth_amt1 = len(r.data["records"])
##    if str(depth) not in depth_dict:
##        depth_dict[str(depth)] = 0
##    depth_dict[str(depth)] += 1
##    u_f = []
##    amt = prev_amt
##    total = prev_total
##    for x in users:
##        a_l = len(users[x])
##        total += a_l
##        amt += 1
##    if total == 0:
##        avg_friends = 0
##        total = 1
##    else:
##        avg_friends = round(total/amt,2)
##    if amt == 0:
##        amt = 1
##    def depth_conv(n1,n2,depth_dict=depth_dict):
##        return depth_dict[str(n2)]/depth_dict[str(n1)]
##    if amt > ng or r.rate_limit.remaining <= 2:
##        try:
##            ng += 5
##            est_users = round((depth_dict[str(9)]/depth_dict[str(2)])*depth_amt1,3)
##            #est_users = round((total/amt)**(max_depth-1),3)
##            curr_dur = (datetime.datetime.utcnow()-start).total_seconds()
##            avg_time_per = round(curr_dur/amt,5)
##            est_remaining = avg_time_per*(est_users-amt)
##            
##            #print(f" | amt: {amt} - total: {total} - avg_friends: {avg_friends} - est_users: {est_users} - curr_dur: {curr_dur} - avg_time_per: {avg_time_per}")
##            print(f'{depth} | {amt}/{est_users} - avg friends: {avg_friends} - {r.rate_limit.remaining}/{r.rate_limit.limit} - Reset in {toolbox.format_time_sec(r.rate_limit.reset)} - {toolbox.format_time_sec(curr_dur)}/{toolbox.format_time_sec(est_remaining)} - Avg Per: {toolbox.format_time_sec(avg_time_per)}')
##        except:
##            curr_dur = (datetime.datetime.utcnow()-start).total_seconds()
##            #print(traceback.format_exc())
##            print(f'{depth} | {amt} - {r.rate_limit.remaining}/{r.rate_limit.limit} - Reset in {toolbox.format_time_sec(r.rate_limit.reset)} - {toolbox.format_time_sec(curr_dur)}')
##    else:
##        amt = len(users) + prev_amt
##    for x in r.data["records"]:
##        i = x["uuidSender"]
##        if i == uuid:
##            i = x["uuidReceiver"]
##        u_f.append(i)
##    users[uuid] = u_f
##    if r.rate_limit.remaining <= 1:
##        sleep(r.rate_limit.reset+1)
##    for x in r.data["records"]:
##        i = x["uuidSender"]
##        if i == uuid:
##            i = x["uuidReceiver"]
##        if i in users:
##            continue
##        try:
##            hypixel_save_friends(i,depth)
##        except:
##            print("Fail")
##            print(traceback.format_exc())
##    if len(users) >= 300:
##        prev_amt += len(users)
##        prev_total += total
##        f = open(f"user_files/basic_users_uuids2_{ng}.json","w+")
##        json.dump(users,f)
##        f.close()
##        users = {}
##    return
##
###uuid = "101bb58=b4a989dd0b91f49257288"
##huser = m.find_user("LegitVic")
##uuid = huser.uuid
##
##hypixel_save_friends(uuid)
##
##print(len(users))
##
##
##f = open("user_uuids.json","w+")
##json.dump(users,f)
##f.close()


pm = m.find_user("dzck")

dt = datetime.datetime.fromtimestamp(152562108)

nt = pm.name_at(dt)

print(repr(nt))

f = open("player.json")
d = json.load(f)
f.close()
f = open("player.json","w+")
json.dump(d,f,indent=2)
f.close()


#for x in d["player"].keys():
#    print(x)

fp = "guild.json"
f = open(fp)
qd = json.load(f)
f.close()
f = open(fp,"w+")
json.dump(qd,f,indent=2)
f.close()


f = open("quests.json")
qd = json.load(f)
f.close()
f = open("quests.json","w+")
json.dump(qd,f,indent=2)
f.close()




rewards_list = []
for x in qd["quests"]:
    y = qd["quests"][x]
    for game_dict in y:
        #print(x)
        rewards_dict = game_dict["rewards"]
        for reward in rewards_dict:
            r_type = reward["type"]
            if r_type not in rewards_list:
                rewards_list.append(r_type)
#for r in rewards_list:
#    print(r)

print(f'\n'+"+"*20+f"\nAmt of rewards: {len(rewards_list)}\n")
    

keys = ["*****************","*****************","*****************"]


h_api = HypixelAPI(keys)
##
##for x in range(1):
##    break
##    print(f'\nx: {x}\n')
##    for k in h_api.auth:
##        print(str(k),k.owner_minecraft,k.total())
##        k._info()
##    sleep(6)


import inspect



def print_info(c,show_values=False,show_type=True):
    longest = 0
    for x in dir(c):
        if not x.startswith("_"):
            y = len(x)
            if longest < y:
                longest = y
    cn = class_name(c)
    if inspect.isclass(c):
        argspec = inspect.getfullargspec(c.__init__)
        a = ""
        if argspec.defaults != None:
            argslen = len(argspec.args)
            defslen = len(argspec.defaults)
            b = []
            for arg in argspec.args[:argslen-defslen]:
                b.append(arg)
            for arg,value in zip(argspec.args[argslen-defslen:],argspec.defaults):
                b.append(f'{arg}={repr(value)}')
            a = ",".join(b)
        else:
            a = ",".join(argspec.args)
        txt = f'{cn}.__init__({a})'
        print(txt)

        print()

    for x in dir(c):
        if not x.startswith("_"):
            y = eval(f'c.{x}')
            if callable(y):
                if not show_type:
                    prefix = ''
                elif inspect.ismethod(y):
                    prefix = 'method    '
                else:
                    prefix = 'function  '
                if inspect.iscoroutine(y) or inspect.iscoroutinefunction(y):
                    prefix += "await "
                a = ""
                try:
                    argspec = inspect.getfullargspec(y)
                    if argspec.defaults != None:
                        argslen = len(argspec.args)
                        defslen = len(argspec.defaults)
                        b = []
                        for arg in argspec.args[:argslen-defslen]:
                            b.append(arg)
                        for arg,value in zip(argspec.args[argslen-defslen:],argspec.defaults):
                            b.append(f'{arg}={repr(value)}')
                        a = ",".join(b)
                    else:
                        a = ",".join(argspec.args)
                except:
                    a = "*error*"
                txt = f'{prefix}{cn}.{x}({a})'
                #print(argspec)
            else:
                if show_type:
                    prefix = 'attrib    '
                else:
                    prefix = ''
                if show_values:
                    txt = prefix
                    a1 = f'{cn}.{x}'
                    a1l = len(a1)
                    txt += a1
                    txt += " "*(len(cn)+longest+2-a1l)
                    txt += repr(y)
                else:
                    txt = f'{prefix}{cn}.{x}'
            print(txt)



#print_info(User)

h_api = HypixelAPI(keys)

##start = datetime.datetime.utcnow()
##for _ in range(amt):
##    #print(_,h_api.cache.is_updated("watch_dog_stats"))
##    #wd = h_api.watch_dog_stats()
##    r = requests.get("https://api.hypixel.net/watchdogstats",params={"key": key.key})
##end = datetime.datetime.utcnow()
##dur = end-start
##print(dur/amt)




class AiohttpResponse:
    def __init__(self,r,elapsed,data):
        self._aiohttp_response = r
        self.elapsed = elapsed
        self.content = data
    async def _load(self):
        r = self._aiohttp_response
        self.raw = r

        self.apparent_encoding = r.get_encoding()
        self.cookies = {}
        for x in r.cookies:
            self.cookies[x] = r.cookies[x].value
        self.encoding = r.get_encoding()
        self.headers = r.headers
        self.history = r.history
        if len(self.history) == 0:
            self.is_redirect = False
        else:
            self.is_redirect = True
        self.links = dict(r.links)
        self.ok = r.ok
        self.reason = r.reason
        self.request = r.request_info
        self.status_code = r.status
        self.url = r.real_url
    def raise_for_status(self):
        return self._aiohttp_response.raise_for_status()
    def json(self):
        return json.loads(self.content)
    @property
    def text(self):
        return str(self.content,self.encoding)

    
    
    async def get(*args,**kwargs):
        start = datetime.datetime.utcnow()
        async with aiohttp.request("get",*args,**kwargs) as r:
            data = await r.read()
        end = datetime.datetime.utcnow()
        ar = AiohttpResponse(r,end-start,data)
        await ar._load()
        return ar
    
    async def ping(*args,**kwargs):
        async with aiohttp.request("get",*args,**kwargs) as r:
            r.close()





#for x in list(aiohttp.ClientRequest.__init__.__annotations__.keys()):
#    print(x)


def iter_dict(d):
    for x in d:
        yield x,d[x]
def schema(d):
    schema_dict = {}
    for key,value in iter_dict(d):
        v_cn = class_name(value)
        if v_cn == "dict":
            schema_dict[key] = schema(value)
        else:
            schema_dict[key] = v_cn
    return schema_dict


f = open("player_schema.json","w+")
json.dump(schema(d),f,indent=2)
f.close()

f = open("player1.json")
d1 = json.load(f)
f.close()
f = open("player1.json","w+")
json.dump(d1,f,indent=2)
f.close()


def common_schema(items):
    schema_dict = None
    for i in items:
        i_cn = class_name(i)
        if i_cn == "dict":
            for x,y in iter_dict(i):
                if class_name(y) != "dict":
                    continue
                s = schema(y)
                if schema_dict == None:
                    schema_dict = s
                else:
                    nd = schema_dict.copy()
                    for k in list(schema_dict.keys()):
                        if k not in s:
                            del nd[k]
                        else:
                            #continue
                            if class_name(schema_dict[k]) == "dict" and class_name(s[k]) == "dict":
                                nd[k] = common_schema([schema_dict,s])
                    schema_dict = nd
    return schema_dict

schema_dict = common_schema([d,d1])
f = open("player_common_schema.json","w+")
json.dump(schema_dict,f,indent=2)
f.close()


vic = MojangAPI.find_user("dzck")#"bugfroggy")    
pm_h = h_api.from_user(vic)
pm_h._player()

f = open("player.json","w+")
json.dump(pm_h.cache["player"].data,f,indent=2)
f.close()


print(pm_h.uuid)

print(pm_h.status())


#url = "https://api.hypixel.net/resources/guilds/permissions"
#url = "https://api.hypixel.net/resources/challenges"
#url = f"https://api.hypixel.net/guild?key=d9995916-322b-player={pm_h.uuid}"
#url = f"https://api.hypixel.net/gameCounts?key=&uuid={pm_h.uuid}"
url = "https://api.hypixel.net/boosters?uuid=e581"
#url = "https://api.hypixel.net/leaderboards"

hr = h_api.request_get(url)
d = hr.data



from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

code = json.dumps(d,indent=1,ensure_ascii=False)
lexer = get_lexer_by_name("json", stripall=True)
formatter = HtmlFormatter(linenos=True, cssclass="source",full=True)
f = open("req_json.html","w+",encoding="utf8")
result = highlight(code, lexer, formatter,f)
f.close()


print(hypixel_level(21826352))


a = pm_h.achievements()

#for x in a:
#    print(x)

for x in h_api.achievements.types:
    print(x.type)

print()
print()

##g = HypixelGuild(hr)
##
##print(g)
##print(g.name)
##print(g.level)
##for r in g.ranks:
##    print(r,len(r.members))
##
##for a in g.achievements():
##    print(a)
##    print(a.achievement.description)
##    print(a.current_amount)
##    print(a.current_tier)
##    print(a.achievement.get_tier(a.current_tier))
##    if a.current_tier != 0:
##        print(a.achievement.get_tier(a.current_tier).description)
##    print(a.achievement.tiers)



gt = GameType.from_str('MCGO')

print(repr(gt))




