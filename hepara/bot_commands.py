import os
from discord.ext import commands

from utils.mcp_helpers import print_mcp_servers
from utils.skill_helpers import print_skills
from utils.paper_helpers import print_papers, update_database

class HeparaCommands(commands.Cog):
    @commands.command(name="help", description="List the available commands of HEPARA")
    async def help(self, ctx: commands.Context):
        help_message = """
            **HEPARA Commands**
            `!help`: Show this commanld list.
            `add_author`: Add an author for citation tracking.
            `rm_author`: Remove an author for citation tracking.
            `!mcp`: List the available MCP servers.
            `!skill`: List the available Skills.
            `!paper`: List the available papers for analysis.
            `!update_db`: Update the local papers database.

            **Chat**
            Mention me with a question to ask HEPARA:
            `@HEPARA summarize arXiv:2401.12345`
        """.strip()
        await ctx.send(help_message)

    @commands.command(name="mcp", description="List the available MCP servers")
    async def mcp(self, ctx: commands.Context):
        mcp_results = print_mcp_servers()
        await ctx.send(mcp_results)

    @commands.command(name="skill", description="List the available Skills")
    async def skill(self, ctx: commands.Context):
        skill_results = print_skills()
        await ctx.send(skill_results)

    @commands.command(name="paper", description="List the available papers for analysis")
    async def paper(self, ctx: commands.Context):
        papers = print_papers()
        await ctx.send(papers)

    @commands.command(name="update_db", description="Update the local papers database")
    async def update_db(self, ctx: commands.Context):
        try:
            results = update_database()
            await ctx.send(results)
        except Exception as e:
            await ctx.send(f"Database update failed: {e}")

    @commands.command(name="author", description="List all authors.")
    async def author(self, ctx: commands.Context):
        authors = os.getenv('AUTHOR')
        if not authors:
            await ctx.send("No author can be tracked.")
        else:
            authors.replace(",", "\n")
            await ctx.send(f"These authors can be tracked:\n{authors}")

    @commands.command(name="add_author", description="Add an author for citation tracking")
    async def add_author(self, ctx: commands.Context, *, name: str):
        authors = os.getenv('AUTHOR')
        if authors:
            authors += f",{name.strip()}"
        else:
            authors = name.strip()

        os.environ['AUTHOR'] = authors
        await ctx.send(f"Author {name} is added. All authors:\n {os.environ['AUTHOR']}")

    @commands.command(name="rm_author", description="Remove an author for citation tracking")
    async def rm_author(self, ctx: commands.Context, *, name: str):
        authors = os.getenv('AUTHOR')
        if not authors:
            await ctx.send("No author can be removed.")
        else:
            authors_list = authors.split(sep=",")
            if name.strip() in authors_list:
                authors_list.remove(name.strip())
                os.environ['AUTHOR'] = ",".join(authors_list)
                await ctx.send(f"Author {name} is removed. All authors:\n {os.environ['AUTHOR']}")
            else:
                await ctx.send(f"{name} is not in the authors list.")
