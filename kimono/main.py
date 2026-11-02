import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from google import genai
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
GEMINI_KEY = os.getenv("GEMINI_KEY")

# Configurar Cliente Gemini AI
ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# Configurar Banco de Dados MongoDB
db_client = AsyncIOMotorClient(MONGO_URI) if MONGO_URI else None
db = db_client["kimono_db"] if db_client is not None else None
warns_collection = db["warnings"] if db is not None else None

# Configurações globais
ticket_config = {
    "cargo_staff_id": None,
    "categoria_id": None,
}

# Cores e Ícones Juminocore (Estética V2)
COLOR_GREEN = 0x7ED957
COLOR_GOLD = 0xFFD700
COLOR_PURPLE = 0x9B59B6
ICON_APPLE = "🍏"
ICON_STAR = "⭐"
ICON_MAGIC = "✨"

class KimonoBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=">",
            intents=discord.Intents.all(),
            help_command=None
        )

    async def setup_hook(self):
        # Sincronização global e instantânea dos Slash Commands
        await self.tree.sync()
        print("🌱 [Kimono] Slash Commands sincronizados globalmente!")

    async def on_ready(self):
        # Força a sincronização na guilda atual para aparecer na hora
        for guild in self.guilds:
            try:
                await self.tree.sync(guild=guild)
                print(f"✨ [Kimono] Comandos sincronizados na guilda: {guild.name}")
            except Exception:
                pass

        print(f"✨ [Kimono] Conectado como {self.user.name} ({self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="a Floresta crescer | >help ou /perguntar"
            )
        )

bot = KimonoBot()

# ==================== SISTEMA DE TICKETS BLINDADO ====================
class TicketControlView(discord.ui.View):
    def __init__(self, opener_id=None):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    @discord.ui.button(label="Atender", style=discord.ButtonStyle.primary, emoji="🌿", custom_id="ticket_claim")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            button.disabled = True
            button.label = f"Atendido por {interaction.user.name}"
            
            embed = interaction.message.embeds[0]
            embed.set_field_at(1, name="✨ Guardião Responsável", value=interaction.user.mention, inline=True)
            
            await interaction.message.edit(embed=embed, view=self)
            await interaction.followup.send(f"🌿 {interaction.user.mention} assumiu o atendimento desta cabana!", ephemeral=False)
        except Exception:
            print("[Erro 067]")
            await interaction.followup.send("🍂 [Erro 067] Não foi possível assumir o atendimento no momento.", ephemeral=True)

    @discord.ui.button(label="Marcar Staff", style=discord.ButtonStyle.secondary, emoji="🔔", custom_id="ticket_ping_staff")
    async def ping_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            role_id = ticket_config.get("cargo_staff_id")
            role_mention = f"<@&{role_id}>" if role_id else "@here"
            await interaction.response.send_message(content=f"🔔 {role_mention}, um usuário precisa de atenção nesta cabana!", ephemeral=False)
        except Exception:
            print("[Erro 067]")
            await interaction.response.send_message("🍂 [Erro 067] Não foi possível marcar os guardiões.", ephemeral=True)

    @discord.ui.button(label="Fechar / Apagar", style=discord.ButtonStyle.danger, emoji="🍂", custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_message("🍂 Esta cabana será fechada e purificada em **25 segundos**...", ephemeral=False)
            
            for remaining in [20, 15, 10, 5]:
                await asyncio.sleep(5)
                try:
                    await interaction.channel.send(f"⏳ Fechando em {remaining} segundos...")
                except:
                    pass
            
            await asyncio.sleep(5)
            await interaction.channel.delete(reason="Ticket fechado pelo sistema Kimono")
        except Exception:
            print("[Erro 067]")

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir Cabana de Ajuda", style=discord.ButtonStyle.success, emoji="🌿", custom_id="kimono_ticket_create")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user

        try:
            ticket_name = f"🌿-ticket-{user.name.lower()}"
            existing_channel = discord.utils.get(guild.text_channels, name=ticket_name)
            
            if existing_channel:
                await interaction.followup.send(f"🍂 Você já possui uma cabana de atendimento aberta em {existing_channel.mention}! `[Erro 067]`", ephemeral=True)
                return

            category = guild.get_channel(ticket_config["categoria_id"]) if ticket_config["categoria_id"] else None
            
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            if ticket_config["cargo_staff_id"]:
                staff_role = guild.get_role(ticket_config["cargo_staff_id"])
                if staff_role:
                    overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

            channel = await guild.create_text_channel(
                name=ticket_name,
                category=category,
                overwrites=overwrites,
                reason="Ticket do sistema Kimono"
            )
            
            role_id = ticket_config.get("cargo_staff_id")
            ping_msg = f"<@&{role_id}>" if role_id else "@here"
            staff_ping = f"<@&{role_id}>" if role_id else "Guardiões"
            
            embed = discord.Embed(
                title=f"{ICON_STAR} Cabana de Atendimento",
                description=f"Olá, {user.mention}! Um guardião Jumino ({staff_ping}) estará com você em breve.\n\nUse os botões abaixo para gerenciar o atendimento.",
                color=COLOR_PURPLE
            )
            embed.add_field(name="👤 Quem Abriu", value=user.mention, inline=True)
            embed.add_field(name="✨ Guardião Responsável", value="*Nenhum ainda*", inline=True)
            embed.set_footer(text="Kimono Tickets • Juminocore V2")
            
            await channel.send(content=ping_msg, embed=embed, view=TicketControlView(opener_id=user.id))
            await interaction.followup.send(f"Sua cabana de atendimento foi criada com sucesso em {channel.mention}!", ephemeral=True)

        except Exception:
            print("[Erro 067]")
            await interaction.followup.send("🍂 Ocorreu um erro ao abrir sua cabana. `[Erro 067]`", ephemeral=True)

# ==================== COMANDOS DE MODERAÇÃO (SLASH & PREFIXO) ====================

# 1. WARN (Individual)
@bot.tree.command(name="warn", description="🍎 [Moderação] Adiciona um aviso (warn) a um membro.")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_warn(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Nenhum motivo especificado."):
    await process_warn(interaction, membro, motivo, is_slash=True)

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def prefix_warn(ctx, membro: discord.Member = None, *, motivo: str = "Nenhum motivo especificado."):
    if not membro:
        return await ctx.send("🍂 Uso correto: `>warn @usuario [motivo]` `[Erro 010]`")
    await process_warn(ctx, membro, motivo, is_slash=False)

async def process_warn(context, membro, motivo, is_slash):
    try:
        if warns_collection is not None:
            await warns_collection.insert_one({"guild_id": context.guild.id, "user_id": membro.id, "reason": motivo})
        
        embed = discord.Embed(title=f"{ICON_APPLE} Aviso Aplicado", description=f"**Membro:** {membro.mention}\n**Motivo:** {motivo}", color=COLOR_GOLD)
        embed.set_footer(text="Kimono Moderation • Juminocore V2")
        
        if is_slash:
            await context.response.send_message(embed=embed)
        else:
            await context.send(embed=embed)
    except Exception:
        print("[Erro 010]")
        msg = "🍂 Falha ao aplicar aviso. `[Erro 010]`"
        await context.response.send_message(msg, ephemeral=True) if is_slash else await context.send(msg)

# 2. WARN LOTE
@bot.tree.command(name="warn_lote", description="🍎 [Moderação] Aplica aviso (warn) em múltiplos usuários por IDs.")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_warn_lote(interaction: discord.Interaction, membros: str, motivo: str = "Nenhum motivo especificado."):
    await process_warn_lote(interaction, membros, motivo, is_slash=True)

@bot.command(name="warn_lote")
@commands.has_permissions(manage_messages=True)
async def prefix_warn_lote(ctx, membros: str = None, *, motivo: str = "Nenhum motivo especificado."):
    if not membros:
        return await ctx.send("🍂 Uso correto: `>warn_lote ID1, ID2 [motivo]` `[Erro 010]`")
    await process_warn_lote(ctx, membros, motivo, is_slash=False)

async def process_warn_lote(context, membros_str, motivo, is_slash):
    if is_slash:
        await context.response.defer(ephemeral=True)

    try:
        ids = [int(i) for i in membros_str.replace(",", " ").split() if i.isdigit()]
        avisados = []
        
        for uid in ids:
            try:
                membro = context.guild.get_member(uid) or await bot.fetch_user(uid)
                if membro:
                    avisados.append(membro.name)
                    if warns_collection is not None:
                        await warns_collection.insert_one({"guild_id": context.guild.id, "user_id": uid, "reason": motivo})
            except:
                pass

        embed = discord.Embed(title=f"{ICON_MAGIC} Avisos em Lote Aplicados", description=f"**Membros:** {', '.join(avisados) if avisados else 'Nenhum'}\n**Motivo:** {motivo}", color=COLOR_GOLD)
        if is_slash:
            await context.followup.send(embed=embed)
        else:
            await context.send(embed=embed)
    except Exception:
        print("[Erro 010]")
        msg = "🍂 Falha ao aplicar avisos em lote. Verifique se os IDs são válidos. `[Erro 010]`"
        if is_slash:
            await context.followup.send(msg, ephemeral=True)
        else:
            await context.send(msg)

# 3. MUTE (Individual)
@bot.tree.command(name="mute", description="🍎 [Moderação] Silencia um membro por tempo determinado (minutos).")
@app_commands.checks.has_permissions(moderate_members=True)
async def slash_mute(interaction: discord.Interaction, membro: discord.Member, minutos: int, motivo: str = "Nenhum motivo especificado."):
    await process_mute(interaction, membro, minutos, motivo, is_slash=True)

@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def prefix_mute(ctx, membro: discord.Member = None, minutos: int = 10, *, motivo: str = "Nenhum motivo especificado."):
    if not membro:
        return await ctx.send("🍂 Uso correto: `>mute @usuario [minutos] [motivo]` `[Erro 010]`")
    await process_mute(ctx, membro, minutos, motivo, is_slash=False)

async def process_mute(context, membro, minutos, motivo, is_slash):
    try:
        duration = discord.utils.utcnow() + discord.timedelta(minutes=minutos)
        await membro.timeout(duration, reason=motivo)
        
        embed = discord.Embed(title=f"{ICON_APPLE} Membro Silenciado", description=f"**Membro:** {membro.mention}\n**Tempo:** {minutos} min\n**Motivo:** {motivo}", color=COLOR_PURPLE)
        if is_slash:
            await context.response.send_message(embed=embed)
        else:
            await context.send(embed=embed)
    except Exception:
        print("[Erro 010]")
        msg = "🍂 Falha ao silenciar membro. `[Erro 010]`"
        await context.response.send_message(msg, ephemeral=True) if is_slash else await context.send(msg)

# 4. MUTE LOTE
@bot.tree.command(name="mute_lote", description="🍎 [Moderação] Silencia múltiplos usuários por IDs.")
@app_commands.checks.has_permissions(moderate_members=True)
async def slash_mute_lote(interaction: discord.Interaction, membros: str, minutos: int, motivo: str = "Nenhum motivo especificado."):
    await process_mute_lote(interaction, membros, minutos, motivo, is_slash=True)

@bot.command(name="mute_lote")
@commands.has_permissions(moderate_members=True)
async def prefix_mute_lote(ctx, membros: str = None, minutos: int = 10, *, motivo: str = "Nenhum motivo especificado."):
    if not membros:
        return await ctx.send("🍂 Uso correto: `>mute_lote ID1, ID2 [minutos] [motivo]` `[Erro 010]`")
    await process_mute_lote(ctx, membros, minutos, motivo, is_slash=False)

async def process_mute_lote(context, membros_str, minutos, motivo, is_slash):
    if is_slash:
        await context.response.defer(ephemeral=True)

    try:
        ids = [int(i) for i in membros_str.replace(",", " ").split() if i.isdigit()]
        silenciados = []
        duration = discord.utils.utcnow() + discord.timedelta(minutes=minutos)

        for uid in ids:
            membro = context.guild.get_member(uid)
            if membro:
                try:
                    await membro.timeout(duration, reason=motivo)
                    silenciados.append(membro.name)
                except:
                    pass

        embed = discord.Embed(title=f"{ICON_MAGIC} Silenciamentos em Lote", description=f"**Membros:** {', '.join(silenciados) if silenciados else 'Nenhum'}\n**Tempo:** {minutos} min\n**Motivo:** {motivo}", color=COLOR_PURPLE)
        if is_slash:
            await context.followup.send(embed=embed)
        else:
            await context.send(embed=embed)
    except Exception:
        print("[Erro 010]")
        msg = "🍂 Falha ao silenciar em lote. Verifique se os IDs são válidos. `[Erro 010]`"
        if is_slash:
            await context.followup.send(msg, ephemeral=True)
        else:
            await context.send(msg)

# 5. BAN (Individual)
@bot.tree.command(name="ban", description="🍎 [Moderação] Bane um membro do servidor.")
@app_commands.checks.has_permissions(ban_members=True)
async def slash_ban(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Nenhum motivo especificado."):
    await process_ban(interaction, membro, motivo, is_slash=True)

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def prefix_ban(ctx, membro: discord.Member = None, *, motivo: str = "Nenhum motivo especificado."):
    if not membro:
        return await ctx.send("🍂 Uso correto: `>ban @usuario [motivo]` `[Erro 010]`")
    await process_ban(ctx, membro, motivo, is_slash=False)

async def process_ban(context, membro, motivo, is_slash):
    try:
        await membro.ban(reason=motivo)
        embed = discord.Embed(title=f"{ICON_APPLE} Membro Banido", description=f"**Membro:** {membro.name}\n**Motivo:** {motivo}", color=COLOR_GREEN)
        if is_slash:
            await context.response.send_message(embed=embed)
        else:
            await context.send(embed=embed)
    except Exception:
        print("[Erro 010]")
        msg = "🍂 Falha ao banir membro. `[Erro 010]`"
        await context.response.send_message(msg, ephemeral=True) if is_slash else await context.send(msg)

# 6. BAN LOTE
@bot.tree.command(name="ban_lote", description="🍎 [Jumino Core] Bane múltiplos usuários em lote por IDs.")
@app_commands.checks.has_permissions(ban_members=True)
async def ban_lote(interaction: discord.Interaction, membros: str, motivo: str = "Nenhum motivo especificado."):
    await process_ban_lote(interaction, membros, motivo, is_slash=True)

@bot.command(name="ban_lote")
@commands.has_permissions(ban_members=True)
async def prefix_ban_lote(ctx, membros: str = None, *, motivo: str = "Nenhum motivo especificado."):
    if not membros:
        return await ctx.send("🍂 Uso correto: `>ban_lote ID1, ID2 [motivo]` `[Erro 010]`")
    await process_ban_lote(ctx, membros, motivo, is_slash=False)

async def process_ban_lote(context, membros_str, motivo, is_slash):
    if is_slash:
        await context.response.defer(ephemeral=True)

    try:
        ids = [int(i) for i in membros_str.replace(",", " ").split() if i.isdigit()]
        banidos = []
        falhas = []

        for user_id in ids:
            try:
                user = await bot.fetch_user(user_id)
                await context.guild.ban(user, reason=motivo)
                banidos.append(f"{user.name} (`{user.id}`)")
            except Exception:
                falhas.append(str(user_id))

        embed = discord.Embed(title=f"{ICON_MAGIC} Limpeza da Floresta — Ban em Lote", color=COLOR_GREEN)
        embed.add_field(name="✅ Membros Banidos", value="\n".join(banidos) if banidos else "Nenhum", inline=False)
        embed.add_field(name="❌ Falhas", value=", ".join(falhas) if falhas else "Nenhuma", inline=False)
        embed.set_footer(text="Kimono Protection • Juminocore V2")

        if is_slash:
            await context.followup.send(embed=embed)
        else:
            await context.send(embed=embed)
    except Exception:
        print("[Erro 010]")
        msg = "🍂 Falha ao executar banimento em lote. `[Erro 010]`"
        if is_slash:
            await context.followup.send(msg, ephemeral=True)
        else:
            await context.send(msg)

# ==================== OUTROS COMANDOS (SETUP, CONFIG, AI) ====================

@bot.tree.command(name="setup_tickets", description="✨ Configura o painel interativo de tickets no canal atual.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    try:
        await interaction.response.send_message("✨ Instalando a Central de Ajuda na floresta...", ephemeral=True)
        embed = discord.Embed(
            title=f"{ICON_APPLE} Central de Ajuda Kimono",
            description="Precisa de suporte ou tem alguma dúvida? Clique no botão abaixo para abrir sua cabana de atendimento privada.",
            color=COLOR_GREEN
        )
        embed.set_footer(text="Kimono Support • Juminocore V2")
        await interaction.channel.send(embed=embed, view=TicketView())
    except Exception:
        print("[Erro 067]")

@bot.command(name="setup_tickets")
@commands.has_permissions(administrator=True)
async def prefix_setup_tickets(ctx):
    try:
        embed = discord.Embed(
            title=f"{ICON_APPLE} Central de Ajuda Kimono",
            description="Precisa de suporte ou tem alguma dúvida? Clique no botão abaixo para abrir sua cabana de atendimento privada.",
            color=COLOR_GREEN
        )
        embed.set_footer(text="Kimono Support • Juminocore V2")
        await ctx.send(embed=embed, view=TicketView())
    except Exception:
        print("[Erro 067]")

@bot.tree.command(name="perguntar", description="✨ Faça uma pergunta ao espírito místico Kimono (IA).")
async def perguntar(interaction: discord.Interaction, pergunta: str):
    await interaction.response.defer(thinking=True)
    if not ai_client:
        return await interaction.followup.send("A IA não foi configurada. `[Erro 042]`", ephemeral=True)
    
    try:
        response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=pergunta)
        resposta_texto = response.text if response and response.text else "Os espíritos da floresta meditaram, mas não trouxeram palavras."
    except Exception:
        print("[Erro 042]")
        resposta_texto = "Os espíritos da floresta estão silenciosos no momento... `[Erro 042]`"

    embed = discord.Embed(title=f"{ICON_MAGIC} Sabedoria dos Juminos", description=resposta_texto[:4000], color=COLOR_GOLD)
    embed.set_footer(text="Kimono AI • Juminocore V2")
    await interaction.followup.send(embed=embed)

@bot.command(name="perguntar")
async def prefix_perguntar(ctx, *, pergunta: str = None):
    if not pergunta:
        return await ctx.send("🍂 Uso correto: `>perguntar [sua dúvida]` `[Erro 042]`")
    if not ai_client:
        return await ctx.send("🍂 A IA não foi configurada. `[Erro 042]`")
    
    try:
        response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=pergunta)
        resposta_texto = response.text if response and response.text else "Os espíritos da floresta meditaram, mas não trouxeram palavras."
    except Exception:
        print("[Erro 042]")
        resposta_texto = "Os espíritos da floresta estão silenciosos no momento... `[Erro 042]`"

    embed = discord.Embed(title=f"{ICON_MAGIC} Sabedoria dos Juminos", description=resposta_texto[:4000], color=COLOR_GOLD)
    embed.set_footer(text="Kimono AI • Juminocore V2")
    await ctx.send(embed=embed)

# ==================== EXECUTAR BOT ====================
if __name__ == "__main__":
    if not TOKEN:
        print("[Erro 060606] DISCORD_TOKEN não encontrado no arquivo .env!")
    else:
        bot.run(TOKEN)