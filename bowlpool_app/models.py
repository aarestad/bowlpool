from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users require an email field")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(_("email address"), unique=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []


class Team(models.Model):
    name = models.CharField(max_length=128, unique=True)
    abbreviation = models.CharField(max_length=4)

    def __str__(self):
        return str(self.name)

    class Meta:
        ordering = ["name"]


class BowlGame(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return str(self.name)

    class Meta:
        ordering = ["name"]


class BowlMatchup(models.Model):
    # TODO: think about how to handle the CFP National Championship matchup without
    # relying on its name
    bowl_game = models.ForeignKey(BowlGame, on_delete=models.CASCADE)
    bowl_year = models.IntegerField(
        db_index=True,
        help_text=_(
            "Year of the matchup if before January 1, otherwise the year before"
        ),
    )
    cfp_playoff_game = models.BooleanField(default=False)
    start_time = models.DateTimeField(help_text=_("Stored as UTC"))
    away_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="away_team",
        blank=True,
        null=True,
    )
    home_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="home_team",
        blank=True,
        null=True,
    )
    home_team_point_spread = models.IntegerField(
        help_text=_(
            "Home team's point spread - negative means the home team "
            "is favored, positive means the away team is favored"
        ),
        blank=True,
        null=True,
    )
    point_spread_extra_half = models.BooleanField(default=False)
    away_team_final_score = models.IntegerField(null=True, blank=True)
    home_team_final_score = models.IntegerField(null=True, blank=True)

    def bowl_favorite(self):
        if not self.home_team or not self.away_team:
            return "?"

        if self.home_team_point_spread == 0 and not self.point_spread_extra_half:
            return "Pick 'em"

        extra_point_five = ".5" if self.point_spread_extra_half else ""

        return (
            f"{self.home_team} by {abs(self.home_team_point_spread)}{extra_point_five}"
            if self.home_team_point_spread < 0
            else f"{self.away_team} by {self.home_team_point_spread}{extra_point_five}"
        )

    def clean(self):
        if (
            self.away_team_final_score is None
            and self.home_team_final_score is not None
            or self.away_team_final_score is not None
            and self.home_team_final_score is None
        ):
            raise ValidationError(_("Score must be set for both teams or neither one"))

    @property
    def final_margin(self):
        """The final margin, if the game is complete: Away score minus Home score
        :return: The final margin, or None if the score is not set
        """

        if self.away_team_final_score is not None and self.home_team_final_score is not None:
            return self.away_team_final_score - self.home_team_final_score

        return None

    @property
    def display_name(self):
        away_team = str(self.away_team) if self.away_team else "?"
        home_team = str(self.home_team) if self.home_team else "?"

        dn = f"{self.bowl_game.name}: {away_team} vs {home_team}"

        if self.cfp_playoff_game:
            dn += " (CFP Semifinal)"

        return dn

    def __str__(self):
        final_score = (
            ""
            if self.away_team_final_score is None or self.home_team_final_score is None
            else f" ({self.away_team_final_score} - {self.home_team_final_score})"
        )

        return f"[{self.bowl_year}] {self.display_name}{final_score}"

    class Meta:
        ordering = ["start_time"]
        constraints = [
            UniqueConstraint(
                fields=["bowl_year", "bowl_game"], name="unique_bowls_for_year"
            )
        ]


class BowlMatchupPick(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bowl_matchup = models.ForeignKey(BowlMatchup, on_delete=models.CASCADE)
    winner = models.ForeignKey(Team, on_delete=models.CASCADE)
    margin = models.IntegerField()

    def __str__(self):
        return f"[{self.user}] {self.bowl_matchup}: {self.winner_and_margin}"

    @property
    def winner_and_margin(self):
        return f"{self.winner} by {self.margin}"

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["user", "bowl_matchup"], name="unique_matchups_for_user"
            )
        ]

    def clean(self):
        if self.margin == 0:
            raise ValidationError(_("Must pick a nonzero margin"))
