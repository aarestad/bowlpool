from typing import Dict, List

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .models import BowlMatchupPick, BowlMatchup, Team
from .forms import BowlPoolUserCreationForm


def register_user(request):
    if request.method == "POST":
        form = BowlPoolUserCreationForm(request.POST)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("year_index"))
    else:
        form = BowlPoolUserCreationForm()

    return render(request, "register.html", {"form": form})


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
    picks_for_year = BowlMatchupPick.objects.filter(
        bowl_matchup__bowl_year=bowl_year, user=request.user
    )

    if not picks_for_year:
        picks_for_year = []

        matchups_for_year = BowlMatchup.objects.filter(bowl_year=bowl_year)

        for bowl_matchup in matchups_for_year:
            picks_for_year.append(
                BowlMatchupPick(user=request.user, bowl_matchup=bowl_matchup)
            )

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
