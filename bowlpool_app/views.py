from typing import Dict, List
import zoneinfo
import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
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

            return HttpResponseRedirect(
                reverse("view_my_picks_for_year", kwargs={"bowl_year": 2023})
            )
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
            "cfp_teams": cfp_teams,
        },
    )


def view_all_picks_for_year(request, bowl_year):
    now = timezone.now()

    if now < datetime.datetime(2023, 12, 26, 0, tzinfo=zoneinfo.ZoneInfo("UTC")):
        return render(
            request,
            "all_picks_for_year.html",
            {"bowl_year": bowl_year, "message": "No peeking until December 26!"},
        )

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


def json_picks_for_year(request, bowl_year):
    all_picks_for_year = BowlMatchupPick.objects.filter(
        bowl_matchup__bowl_year=bowl_year,
    ).values(
        "bowl_matchup__bowl_game__name",
        "bowl_matchup__start_time",
        "bowl_matchup__away_team__name",
        "bowl_matchup__home_team__name",
        "user__first_name",
        "user__last_name",
        "winner__name",
        "margin",
    )

    picks_by_bowl_game: Dict[BowlMatchup, List[BowlMatchupPick]] = {}

    # TODO there's a collections function that does this in the Python stdlib
    for pick in all_picks_for_year:
        if pick["bowl_matchup__bowl_game__name"] not in picks_by_bowl_game:
            picks_by_bowl_game[pick["bowl_matchup__bowl_game__name"]] = [pick]
        else:
            picks_by_bowl_game[pick["bowl_matchup__bowl_game__name"]].append(pick)

    picks_list = []

    for matchup, picks in picks_by_bowl_game.items():
        picks_list.append(
            {
                "matchup": {
                    "bowl_game": matchup,
                    "start_time": picks[0]["bowl_matchup__start_time"],
                    "home_team": picks[0]["bowl_matchup__home_team__name"],
                    "away_team": picks[0]["bowl_matchup__away_team__name"],
                },
                "picks": [
                    {
                        "name": " ".join((p["user__first_name"], p["user__last_name"])),
                        "winner": p["winner__name"],
                        "margin": p["margin"],
                    }
                    for p in picks
                ],
            }
        )

    return JsonResponse(picks_list, safe=False)


@login_required
def submit_my_picks_for_year(request, bowl_year):
    picks_for_matchups = {}
    now = timezone.now()

    # TODO: create a custom form for picks
    for form_key in request.POST.keys():
        if "-" not in form_key:
            continue

        key, matchup_type = form_key.split("-")
        pick_for_matchup = picks_for_matchups.get(key, {})
        pick_for_matchup[matchup_type] = request.POST[form_key]
        picks_for_matchups[key] = pick_for_matchup

    champ_matchup_id = None
    champ_pick = None

    for matchup_id, pick in picks_for_matchups.items():
        bowl_matchup = BowlMatchup.objects.get(id=matchup_id)

        if now >= bowl_matchup.start_time:
            continue

        if bowl_matchup.bowl_game.name == "CFP National Championship":
            # we'll deal with this after everything else is persisted
            champ_matchup_id = matchup_id
            champ_pick = pick
            continue

        if not pick["winner"] or not pick["margin"]:
            messages.error(
                request, _(f"Matchup {bowl_matchup.display_name} not picked")
            )

            continue

        winner = Team(id=pick["winner"])
        margin = int(pick["margin"])

        try:
            db_pick = BowlMatchupPick.objects.get(
                user=request.user, bowl_matchup=bowl_matchup
            )

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

    if not champ_pick["winner"] or not champ_pick["margin"]:
        messages.error(request, _("CFP National Championship not picked"))
    else:
        playoff_picks = list(
            BowlMatchupPick.objects.filter(
                user=request.user, bowl_matchup__cfp_playoff_game=True
            )
        )

        if len(playoff_picks) != 2:
            messages.error(request, _("Pick the CFP semifinal games before the final!"))
        else:
            print(champ_pick["winner"])
            champ_winner = Team(id=int(champ_pick["winner"]))
            champ_margin = int(champ_pick["margin"])

            if not any(champ_winner.id == pick.winner.id for pick in playoff_picks):
                messages.error(
                    request, _("Champ pick must be one of your semifinal winners")
                )
            else:
                champ_matchup = BowlMatchup.objects.get(id=champ_matchup_id)

                if now < champ_matchup.start_time:
                    try:
                        db_pick = BowlMatchupPick.objects.get(
                            user=request.user, bowl_matchup=champ_matchup
                        )

                        db_pick.winner = champ_winner
                        db_pick.margin = champ_margin
                    except BowlMatchupPick.DoesNotExist:
                        db_pick = BowlMatchupPick(
                            user=request.user,
                            bowl_matchup=champ_matchup,
                            winner=champ_winner,
                            margin=champ_margin,
                        )

                    db_pick.full_clean()
                    db_pick.save()

    return HttpResponseRedirect(reverse("view_my_picks_for_year", args=(bowl_year,)))
