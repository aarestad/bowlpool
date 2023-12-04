from typing import Dict, List

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .models import BowlMatchupPick, BowlMatchup, Team
from .forms import BowlPoolUserCreationForm


def register_user(request):
    if request.method == "POST":
        form = BowlPoolUserCreationForm(request.POST)

        if form.is_valid():
            form.save()

            new_user = authenticate(
                username=form.cleaned_data["email"],
                password=form.cleaned_data["password1"],
            )

            login(request, new_user)

            return HttpResponseRedirect(reverse("year_index"))
    else:
        form = BowlPoolUserCreationForm()

    return render(request, "registration/register.html", {"form": form})


def year_index(request):
    try:
        years = (
            BowlMatchup.objects.order_by("bowl_year")
            .values_list("bowl_year")
            .distinct()
        )[0]
    except IndexError:
        years = []

    return render(
        request,
        "year_index.html",
        {
            "years": years,
        },
    )


@login_required
def view_my_picks_for_year(request, bowl_year):
    matchups_for_year = BowlMatchup.objects.filter(bowl_year=bowl_year)

    picks_for_year = list(
        BowlMatchupPick.objects.filter(
            bowl_matchup__bowl_year=bowl_year, user=request.user
        )
    )

    picked_matchups = [p.bowl_matchup for p in picks_for_year]

    cfp_matchups = BowlMatchup.objects.filter(
        bowl_year=bowl_year, cfp_playoff_game=True
    ).select_related("home_team", "away_team")

    cfp_teams = [t for m in cfp_matchups for t in [m.home_team, m.away_team]]

    for m in matchups_for_year:
        if m not in picked_matchups:
            picks_for_year.append(BowlMatchupPick(user=request.user, bowl_matchup=m))

    picks_for_year.sort(key=lambda m: m.bowl_matchup.start_time)

    return render(
        request,
        "user_picks_for_year.html",
        {
            "bowl_year": bowl_year,
            "picks_for_year": picks_for_year,
        },
    )


def view_all_picks_for_year(request, bowl_year):
    all_picks_for_year = BowlMatchupPick.objects.filter(
        bowl_matchup__bowl_year=bowl_year,
    )

    picks_by_bowl_game: Dict[BowlMatchup, List[BowlMatchupPick]] = {}

    # TODO there's a collections function that does this in the Python stdlib
    for pick in all_picks_for_year:
        if pick.bowl_matchup not in picks_by_bowl_game:
            picks_by_bowl_game[pick.bowl_matchup] = [pick]
        else:
            picks_by_bowl_game[pick.bowl_matchup].append(pick)

    for pick_list in picks_by_bowl_game.values():
        pick_list.sort(
            key=lambda p: p.user.last_name.lower() + p.user.first_name.lower()
        )

    return render(
        request,
        "all_picks_for_year.html",
        {
            "bowl_year": bowl_year,
            "picks_for_year": picks_by_bowl_game,
        },
    )


@login_required
def submit_my_picks_for_year(request, bowl_year):
    picks_for_matchups = {}
    new_picks = []

    for form_key in request.POST.keys():
        if "-" not in form_key:
            continue

        key, type = form_key.split("-")
        pick_for_matchup = picks_for_matchups.get(key, {})
        pick_for_matchup[type] = request.POST[form_key]
        picks_for_matchups[key] = pick_for_matchup

    for matchup_id, pick in picks_for_matchups.items():
        if not pick["winner"] or not pick["margin"]:
            bowl_matchup = BowlMatchup.objects.get(id=matchup_id)

            messages.error(
                request, _(f"Matchup {bowl_matchup.display_name} not picked")
            )

            continue

        bowl_matchup = BowlMatchup(id=matchup_id)
        winner = Team(id=pick["winner"])
        margin = int(pick["margin"])

        try:
            db_pick = BowlMatchupPick.objects.get(
                user=request.user, bowl_matchup=bowl_matchup
            )

            # TODO: if db_pick.bowl_matchup.start_time <= now, return an error

            db_pick.winner = winner
            db_pick.margin = margin
        except BowlMatchupPick.DoesNotExist:
            db_pick = BowlMatchupPick(
                user=request.user,
                bowl_matchup=bowl_matchup,
                winner=winner,
                margin=margin,
            )

        db_pick.full_clean()
        db_pick.save()
        new_picks.append(db_pick)

    return HttpResponseRedirect(reverse("view_my_picks_for_year", args=(bowl_year,)))
