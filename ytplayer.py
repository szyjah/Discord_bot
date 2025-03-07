import asyncio
import discord
from discord.ext import commands
import re
import random

import datetime
import youtube_dl
import urllib.request

import logger as log
logger = log.getLogger(__name__)

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn'}
class Song():
    def __init__(self, url):
        self.url = url
        ydl = youtube_dl.YoutubeDL({'outtmpl': '%(id)s.%(ext)s', 'quiet': True})
        with ydl:
            result = ydl.extract_info(url, download=False, )
        if 'entries' in result:
            self.video = result['entries'][0]
        else:
            self.video = result
        
        self.title = result["title"]         
        self.is_live = False
        if result["is_live"] == True:
            self.is_live = True
            return      
        self.duration = str(datetime.timedelta(seconds=result["duration"]))
        for x in result["formats"]:
            if x["format_id"] == "251":
                self.audio_url = x["url"]
            elif x["format_id"] == "250":
                self.audio_url = x["url"]
            elif x["format_id"] == "249":
                self.audio_url = x["url"]
        self.thumbnail = result["thumbnail"]

def find_video_url(args):
    video_id = None
    if len(args) == 1:
        web_link_regex_long = r'(https://)?(www\.)?youtube\.com/watch\?.*v=(\S{11}).*'
        web_link_regex_short = r'(https://)?youtu\.be/(\S{11}).*'
        match_long = re.match(web_link_regex_long, args[0])
        match_short = re.match(web_link_regex_short, args[0])
        if match_long != None:
            video_id = match_long[3]
        elif match_short != None:
            video_id = match_short[2]

    if video_id == None:
        search = ""
        for x in args:
            search = search + str(x) + "+" 
        html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + search)
        video_id = re.findall(r"watch\?v=(\S{11})", html.read().decode())[0]
    
    return ("https://www.youtube.com/watch?v=" + video_id)

class YTPlayer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice = None
        self.queue = []

    def cog_unload(self):
        pass

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')
        return True
    
    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send("Nie mam ochoty działać poprawnie | "+ str(error)) 

    @commands.command(name='play')
    async def _play(self,ctx: commands.Context, *args):
        """Play audio form youtube. Uses first result of a youtube search."""
        if len(args) == 0:
            await ctx.send("pierdol sie")
        else:
            if not ctx.message.author.voice:
                await ctx.send("You need to be in a vc to use this command")
            else:
                channel = ctx.message.author.voice.channel
                check_bot_vclist = len(self.bot.voice_clients) != 0
                if check_bot_vclist:
                    while not self.voice:
                        await asyncio.sleep(1)

                if check_bot_vclist and self.voice.channel is not channel:
                    await ctx.send("youre in a wrong vc fook oof")
                else:
                    video_url = find_video_url(args)
                    song = Song(video_url)
                    if song.is_live == True:
                        await ctx.send("'" + song.title + "' is a stream, you doofus!" )
                        return
                    self.queue.append(song)

                    if len(self.bot.voice_clients) != 0:
                        embed_title = "Postion " + str(len(self.queue)) + " in queue"
                        e = discord.Embed(title=embed_title, description=f"Title: *** {song.title} *** \nTime: {song.duration}", url=song.url)
                        e.set_thumbnail(url=song.thumbnail)
                        await ctx.send(embed=e)
                    else:
                        self.voice = await channel.connect() 
                        while len(self.queue) > 0:  
                            poped_song = self.queue.pop(0)

                            url = poped_song.audio_url
                            e = discord.Embed(title='Now playing', description=f"Title: *** {poped_song.title} *** \nTime: {poped_song.duration}", url=poped_song.url)
                            e.set_thumbnail(url=poped_song.thumbnail)
                            await ctx.send(embed=e)
                                            
                            source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
                            self.voice.play(source)
                            while self.voice.is_playing() or self.voice.is_paused():
                                await asyncio.sleep(1) 
                        await self.voice.disconnect() 
                        self.voice = None 
                            
    @commands.command(name='pause')
    async def _pause(self,ctx: commands.Context):
        """Pause currently played sound"""
    
        self.voice.pause()

    @commands.command(name='resume')
    async def _resume(self,ctx: commands.Context):
        """Resume audio playback"""  
        
        self.voice.resume()

    @commands.command(name='skip')
    async def _skip(self,ctx: commands.Context):
        """Skip a song"""
        
        self.voice.stop()

    @commands.command(name='stop')
    async def _stop(self,ctx: commands.Context):
        """Stop audio playback"""
        
        self.queue = []
        self.voice.stop()

    @commands.command(name='move')
    async def _move(self,ctx: commands.Context, old_pos, new_pos):
        """Change postition of a song in queue"""
        
        queue_len = len(self.queue)
        if queue_len == 0:
            await ctx.send("what do you want to move you dingus")
        else:
            try:
                old_pos = int(old_pos) - 1
                new_pos = int(new_pos) - 1
                queue_range = range(0, queue_len)
                if old_pos in queue_range and new_pos in queue_range:
                    self.queue.insert(new_pos, self.queue.pop(old_pos))
                else:
                    await ctx.send("youh numbhas ar not in tha queue")
            except ValueError:
                await ctx.send("you idiot itsa not a numbha")
    
    @commands.command(name='clear')
    async def _clear(self,ctx: commands.Context):
        """Empty queue"""
        
        self.queue = []
    
    @commands.command(name='queue')
    async def _queue(self,ctx: commands.Context):
        """Show queue"""

        if len(self.queue) == 0:
            await ctx.send("Queue is empty you dingus")
        else:
            number = 1
            string = ""
            for x in self.queue:
                string = string + str(number) + ". " + x.title + "\n"
                number = number + 1
            e = discord.Embed(title='Queue', description=string)
            await ctx.send(embed=e)

    @commands.command(name='shuffle')
    async def _shuffle(self,ctx: commands.Context):
        """Shuffle queue"""

        if len(self.queue) == 0:
            await ctx.send("Queue is empty you dingus")
        else:
            random.shuffle(self.queue)
            await ctx.send("Queue (maybe) shuffled")
    
    @commands.command(name='remove')
    async def _remove(self,ctx: commands.Context, pos):
        """Remove song from queue"""

        if len(self.queue) == 0:
            await ctx.send("Queue is empty you dingus")
        else:
            try:
                song = self.queue.pop(int(pos) - 1)
                await ctx.send(song.title + " removed from queue")
            except ValueError:
                await ctx.send("you idiot itsa not a numbha")
        


async def setup(bot):
    """Add component"""
    
    logger.info("Adding cog " + __name__)
    await bot.add_cog(YTPlayer(bot))
