import os
from discord.ext import commands

from utils.mcp_helpers import print_mcp_servers
from utils.skill_helpers import print_skills
from utils.paper_helpers import print_papers, update_database
from utils.categories import all_categories

class HeparaCommands(commands.Cog):
    @commands.command(name="help", description="List the available commands of HEPARA")
    async def help(self, ctx: commands.Context):
        help_message = """
            **HEPARA Commands**
            `!help`: Show this commanld list.
            `author`: List all authors.
            `add_author`: Add an author for citation tracking.
            `rm_author`: Remove an author for citation tracking.
            `add_category`: Add an arXiv category for tracking or recommendation.
            `rm_category`: Remove an arXiv category for tracking or recommendation.
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
            authors = authors.replace(",", "\n")
            await ctx.send(f"These authors can be tracked:\n{authors}")

    @commands.command(name="add_author", description="Add an author for citation tracking")
    async def add_author(self, ctx: commands.Context, *, name: str):
        authors = os.getenv('AUTHOR')
        if authors:
            authors += f",{name.strip()}"
        else:
            authors = name.strip()

        os.environ['AUTHOR'] = authors
        await ctx.send(f"Author {name} has been added. All authors:\n {os.environ['AUTHOR']}")

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
                await ctx.send(f"Author {name} has been removed. All authors:\n {os.environ['AUTHOR']}")
            else:
                await ctx.send(f"{name} is not in the authors list.")

    @commands.command(name="category", description="List all categories")
    async def category(self, ctx:commands.Context):
        categories = os.getenv('CATEGORIES')
        if not categories:
            await ctx.send("No category can be tracked.")
        else:
            categories = categories.replace(",", "\n")
            await ctx.send(f"These categories can be tracked:\n{categories}")

    @commands.command(name="add_category", description="Add an arXiv category for tracking or recommendation")
    async def add_category(self, ctx: commands.Context, *, category: str):        
        if category.strip() not in all_categories.keys():
            await ctx.send(f"{category} is not a valid arXiv category.")
            return
        
        categories = os.getenv("CATEGORIES")
        if categories:
            categories += f",{category.strip()}"
        else:
            categories = category.strip()

        os.environ["CATEGORIES"] = categories
        await ctx.send(f"Category {category} has been added. All categories:\n {os.environ["CATEGORIES"]}")

    @commands.command(name="rm_category", description="Remove an arXiv category for tracking or recommendation")
    async def rm_category(self, ctx: commands.Context, *, category: str):
        if category.strip() not in all_categories.keys():
            await ctx.send(f"{category} is not a valid arXiv category.")
            return
        
        categories = os.getenv("CATEGORIES")
        if not categories:
            await ctx.send("No category can be removed.")
        else:
            categories_list = categories.split(sep=",")
            if category.strip() in categories_list:
                categories_list.remove(category.strip())
                os.environ['CATEGORIES'] = ",".join(categories_list)
                await ctx.send(f"Category {category.strip()} has been removed. All categories:\n {os.environ['CATEGORIES']}")
            else:
                await ctx.send(f"Category {category} is not in the categories list.")
