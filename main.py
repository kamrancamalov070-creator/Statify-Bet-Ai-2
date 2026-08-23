"""
Statify Bet AI
A football prediction mobile app built with Flet.

Screens:
  1. Splash Screen        -> animated logo/branding, auto-navigates after 3s
  2. Auth / Onboarding    -> ToS checkbox, 18+ checkbox, Google Sign-In, Continue button
  3. Main App             -> Bottom navigation with Home (predictions) and VIP (exclusive) tabs

Run with:
    pip install flet
    flet run statify_bet_ai.py          # desktop
    flet run --web statify_bet_ai.py    # browser
    flet run --android / --ios          # mobile (via flet build)
"""

import asyncio
import flet as ft

# ---------------------------------------------------------------------------
# Brand palette
# ---------------------------------------------------------------------------
NAVY = "#0B1F3A"          # deep navy blue (background / primary)
NAVY_DARK = "#071528"     # darker navy for cards/surfaces
WHITE = "#FFFFFF"
GREEN = "#2ECC71"         # electric/mint green (accent)
GREEN_DARK = "#1FA85C"
MUTED = "#8CA0BF"         # muted slate for secondary text
CARD_BG = "#10284A"


# ---------------------------------------------------------------------------
# Simple in-memory "session" — replace with real state management as needed
# ---------------------------------------------------------------------------
class AppState:
    def __init__(self):
        self.google_signed_in = False
        self.user_name = None
        self.is_vip = False


state = AppState()


def main(page: ft.Page):
    page.title = "Statify Bet AI"
    page.bgcolor = NAVY
    page.padding = 0
    page.window.width = 400
    page.window.height = 800
    page.theme_mode = ft.ThemeMode.DARK
    page.fonts = {}
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # -----------------------------------------------------------------
    # Navigation helper
    # -----------------------------------------------------------------
    def show(view_controls: list):
        page.controls.clear()
        page.controls.extend(view_controls)
        page.update()

    # ===================================================================
    # 1. SPLASH SCREEN
    # ===================================================================
    def build_splash():
        logo_circle = ft.Container(
            width=110,
            height=110,
            border_radius=55,
            bgcolor=NAVY_DARK,
            border=ft.Border.all(3, GREEN),  # ✅ düzəldildi
            alignment=ft.Alignment(0, 0),    # ✅ düzəldildi (əvvəl ft.alignment.center)
            content=ft.Icon(ft.Icons.SPORTS_SOCCER, color=GREEN, size=56),
            scale=ft.Scale(0.6),
            opacity=0,
            animate_scale=ft.Animation(900, ft.AnimationCurve.EASE_OUT),
            animate_opacity=ft.Animation(900, ft.AnimationCurve.EASE_OUT),
        )

        title_text = ft.Text(
            "STATIFY",
            size=32,
            weight=ft.FontWeight.BOLD,
            color=WHITE,
            opacity=0,
            animate_opacity=ft.Animation(1000, ft.AnimationCurve.EASE_OUT),
        )
        subtitle_text = ft.Text(
            "BET  AI",
            size=20,
            weight=ft.FontWeight.W_600,
            color=GREEN,
            opacity=0,
            animate_opacity=ft.Animation(1200, ft.AnimationCurve.EASE_OUT),
        )
        tagline = ft.Text(
            "AI-Powered Football Predictions",
            size=13,
            color=MUTED,
            opacity=0,
            animate_opacity=ft.Animation(1400, ft.AnimationCurve.EASE_OUT),
        )

        progress = ft.ProgressRing(
            width=22, height=22, stroke_width=2.5, color=GREEN, opacity=0,
            animate_opacity=ft.Animation(1400, ft.AnimationCurve.EASE_OUT),
        )

        column = ft.Column(
            controls=[
                logo_circle,
                ft.Container(height=18),
                title_text,
                subtitle_text,
                ft.Container(height=30),
                tagline,
                ft.Container(height=24),
                progress,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        view = ft.Container(
            content=column,
            alignment=ft.Alignment(0, 0),    # ✅ düzəldildi
            expand=True,
            bgcolor=NAVY,
        )

        async def animate_and_continue():
            await asyncio.sleep(0.15)
            logo_circle.opacity = 1
            logo_circle.scale = ft.Scale(1.0)
            title_text.opacity = 1
            subtitle_text.opacity = 1
            tagline.opacity = 1
            progress.opacity = 1
            page.update()

            await asyncio.sleep(3)
            show(build_auth())

        page.run_task(animate_and_continue)
        return [view]

    # ===================================================================
    # 2. AUTH / ONBOARDING SCREEN
    # ===================================================================
    def build_auth():
        tos_checkbox = ft.Checkbox(
            label="I agree to the Terms of Service & Privacy Policy",
            label_style=ft.TextStyle(color=WHITE, size=13),
            check_color=NAVY,
            fill_color=GREEN,
            value=False,
        )
        age_checkbox = ft.Checkbox(
            label="I confirm that I am 18 years of age or older",
            label_style=ft.TextStyle(color=WHITE, size=13),
            check_color=NAVY,
            fill_color=GREEN,
            value=False,
        )

        google_status_text = ft.Text(
            "Not signed in", size=12, color=MUTED, italic=True
        )

        continue_button = ft.ElevatedButton(
            text="Continue",
            width=320,
            height=50,
            disabled=True,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DISABLED: NAVY_DARK,
                    ft.ControlState.DEFAULT: GREEN,
                },
                color={
                    ft.ControlState.DISABLED: MUTED,
                    ft.ControlState.DEFAULT: NAVY,
                },
                shape=ft.RoundedRectangleBorder(radius=12),
                text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, size=16),
            ),
        )

        def refresh_continue_state(*_):
            continue_button.disabled = not (
                tos_checkbox.value and age_checkbox.value and state.google_signed_in
            )
            page.update()

        tos_checkbox.on_change = refresh_continue_state
        age_checkbox.on_change = refresh_continue_state

        async def handle_google_sign_in(e):
            google_button.disabled = True
            google_button.text = "Signing in..."
            page.update()
            await asyncio.sleep(1.2)

            state.google_signed_in = True
            state.user_name = "Google User"
            google_button.text = "Signed in with Google"
            google_button.icon = ft.Icons.CHECK_CIRCLE
            google_button.bgcolor = GREEN_DARK
            google_status_text.value = f"Signed in as {state.user_name}"
            google_status_text.color = GREEN
            google_status_text.italic = False
            refresh_continue_state()

        google_button = ft.ElevatedButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.G_MOBILEDATA, size=26, color=NAVY),
                    ft.Text("Sign in with Google", weight=ft.FontWeight.W_600, color=NAVY),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6,
            ),
            width=320,
            height=50,
            bgcolor=WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            on_click=handle_google_sign_in,
        )

        def go_to_app(e):
            show(build_main_app())

        continue_button.on_click = go_to_app

        header = ft.Column(
            controls=[
                ft.Icon(ft.Icons.SPORTS_SOCCER, color=GREEN, size=48),
                ft.Container(height=8),
                ft.Text("Statify Bet AI", size=26, weight=ft.FontWeight.BOLD, color=WHITE),
                ft.Text(
                    "Smarter predictions, powered by data.",
                    size=13,
                    color=MUTED,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        )

        card = ft.Container(
            width=340,
            padding=24,
            border_radius=18,
            bgcolor=CARD_BG,
            content=ft.Column(
                controls=[
                    ft.Text("Get Started", size=18, weight=ft.FontWeight.BOLD, color=WHITE),
                    ft.Container(height=6),
                    google_button,
                    google_status_text,
                    ft.Divider(color=NAVY_DARK, height=28),
                    tos_checkbox,
                    age_checkbox,
                    ft.Container(height=10),
                    continue_button,
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        view = ft.Container(
            expand=True,
            bgcolor=NAVY,
            alignment=ft.Alignment(0, 0),    # ✅ düzəldildi
            content=ft.Column(
                controls=[header, ft.Container(height=28), card],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )
        return [view]

    # ===================================================================
    # 3. MAIN APP — Home & VIP tabs with bottom navigation
    # ===================================================================
    def build_main_app():

        # ---- sample prediction data (wire up to your real AI backend) ----
        sample_predictions = [
            {"match": "Real Madrid vs Barcelona", "league": "La Liga",
             "pick": "Over 2.5 Goals", "confidence": 87},
            {"match": "Man City vs Arsenal", "league": "Premier League",
             "pick": "Man City Win", "confidence": 74},
            {"match": "Bayern vs Dortmund", "league": "Bundesliga",
             "pick": "BTTS - Yes", "confidence": 81},
        ]

        vip_predictions = [
            {"match": "PSG vs Marseille", "league": "Ligue 1",
             "pick": "PSG -1.5 Handicap", "confidence": 91},
            {"match": "Juventus vs Inter", "league": "Serie A",
             "pick": "Under 2.5 Goals", "confidence": 88},
        ]

        def prediction_card(p, locked=False):
            content = ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(p["league"], size=11, color=GREEN, weight=ft.FontWeight.W_600),
                            ft.Container(expand=True),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                border_radius=8,
                                bgcolor=NAVY,
                                content=ft.Text(f'{p["confidence"]}%', size=11, color=GREEN,
                                                 weight=ft.FontWeight.BOLD),
                            ),
                        ],
                    ),
                    ft.Text(p["match"], size=15, weight=ft.FontWeight.BOLD, color=WHITE),
                    ft.Container(height=4),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.INSIGHTS, size=16, color=MUTED),
                            ft.Text(
                                "🔒 VIP Members Only" if locked else p["pick"],
                                size=13,
                                color=MUTED if locked else WHITE,
                                italic=locked,
                            ),
                        ],
                        spacing=6,
                    ),
                ],
                spacing=6,
            )
            return ft.Container(
                padding=16,
                border_radius=14,
                bgcolor=CARD_BG,
                border=ft.Border.all(1, GREEN_DARK if not locked else NAVY_DARK),  # ✅ düzəldildi
                content=content,
            )

        # ---------------- HOME TAB ----------------
        home_view = ft.Container(
            expand=True,
            padding=ft.padding.only(left=18, right=18, top=24, bottom=10),
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("Welcome back 👋", size=13, color=MUTED),
                                    ft.Text("Today's Predictions", size=22,
                                            weight=ft.FontWeight.BOLD, color=WHITE),
                                ],
                                spacing=2,
                            ),
                            ft.Container(expand=True),
                            ft.CircleAvatar(
                                content=ft.Icon(ft.Icons.PERSON, color=NAVY),
                                bgcolor=GREEN,
                                radius=20,
                            ),
                        ]
                    ),
                    ft.Container(height=18),
                    ft.Column(
                        controls=[prediction_card(p) for p in sample_predictions],
                        spacing=14,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                ],
                expand=True,
            ),
        )

        # ---------------- VIP TAB ----------------
        def unlock_vip(e):
            state.is_vip = True
            show(build_main_app())
            nav.selected_index = 1
            page.update()

        if state.is_vip:
            vip_body = ft.Column(
                controls=[prediction_card(p) for p in vip_predictions],
                spacing=14,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )
        else:
            vip_body = ft.Column(
                controls=[
                    ft.Container(height=20),
                    ft.Icon(ft.Icons.WORKSPACE_PREMIUM, color=GREEN, size=64),
                    ft.Container(height=10),
                    ft.Text("Unlock VIP Predictions", size=20, weight=ft.FontWeight.BOLD,
                            color=WHITE, text_align=ft.TextAlign.CENTER),
                    ft.Text(
                        "Get exclusive high-confidence picks, deep statistical\n"
                        "breakdowns, and early access to daily predictions.",
                        size=13, color=MUTED, text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=20),
                    *[prediction_card(p, locked=True) for p in vip_predictions],
                    ft.Container(height=20),
                    ft.ElevatedButton(
                        text="Upgrade to VIP",
                        width=280,
                        height=50,
                        style=ft.ButtonStyle(
                            bgcolor=GREEN,
                            color=NAVY,
                            shape=ft.RoundedRectangleBorder(radius=12),
                            text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, size=16),
                        ),
                        on_click=unlock_vip,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )

        vip_view = ft.Container(
            expand=True,
            padding=ft.padding.only(left=18, right=18, top=24, bottom=10),
            content=vip_body,
        )

        body_stack = ft.Container(content=home_view, expand=True)

        def on_nav_change(e):
            index = e.control.selected_index
            body_stack.content = home_view if index == 0 else vip_view
            page.update()

        nav = ft.NavigationBar(
            selected_index=0,
            bgcolor=NAVY_DARK,
            indicator_color=GREEN,
            on_change=on_nav_change,
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.SPORTS_SOCCER_OUTLINED,
                    selected_icon=ft.Icon(ft.Icons.SPORTS_SOCCER, color=NAVY),
                    label="Home",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.WORKSPACE_PREMIUM_OUTLINED,
                    selected_icon=ft.Icon(ft.Icons.WORKSPACE_PREMIUM, color=NAVY),
                    label="VIP",
                ),
            ],
        )

        page.navigation_bar = nav

        root = ft.Container(
            expand=True,
            bgcolor=NAVY,
            content=body_stack,
        )
        return [root]

    # -----------------------------------------------------------------
    # Kick things off with the splash screen
    # -----------------------------------------------------------------
    page.navigation_bar = None
    show(build_splash())


if __name__ == "__main__":
    ft.run(main)
