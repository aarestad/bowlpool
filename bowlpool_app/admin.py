from django.contrib import admin
from .models import User, Team, BowlGame, BowlMatchup, BowlMatchupPick

admin.site.register(Team)
admin.site.register(BowlGame)
admin.site.register(BowlMatchup)
admin.site.register(BowlMatchupPick)
admin.site.register(User)
