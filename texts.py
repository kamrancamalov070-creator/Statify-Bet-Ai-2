# texts.py
# All user-facing strings live here, split by language code ("tr" / "en").
# Add a new language by adding a new top-level key with the same fields.

TEXTS = {
    "tr": {
        "welcome": (
            "Merhaba {name}! 👋\n\n"
            "*Kuponcent*'e hoş geldin — uluslararası maçlar için profesyonel "
            "bahis analizleri ve tahminler sunan projemize katıldığın için teşekkürler.\n\n"
            "Aşağıdaki menüden istediğin bölüme göz atabilirsin."
        ),
        "menu_prompt": "Ne yapmak istersin?",
        "menu_tips": "⚽ Tahminler",
        "menu_history": "📜 Geçmiş",
        "menu_vip": "⭐ VIP",
        "menu_support": "🛠 Destek",
        "menu_language": "🌐 Dil",
        "tips_title": "📅 Aktif maçlar — analiz için birini seç:",
        "no_matches": "Şu anda aktif maç bulunmuyor. Daha sonra tekrar kontrol et!",
        "match_not_found": "Bu maç artık mevcut değil.",
        "back": "🔙 Geri",
        "vip_coming_soon": "⭐ VIP paketimiz çok yakında burada! Gelişmeleri takipte kal.",
        "support_text": (
            "🛠 Destek\n\n"
            "Sorunların, önerilerin veya iş birliği taleplerin için "
            "bize doğrudan ulaşabilirsin:\n👉 @kamrancamlv"
        ),
        "history_text": (
            "📜 Geçmiş tahminler bölümü yakında burada olacak.\n"
            "Şimdilik güncel maçları 'Tahminler' bölümünden takip edebilirsin."
        ),
        "choose_language_prompt": "🌐 Lütfen dilinizi seçin / Please choose your language:",
    },
    "en": {
        "welcome": (
            "Hi {name}! 👋\n\n"
            "Welcome to *Kuponcent* — our project delivering professional betting "
            "analysis and predictions for international matches.\n\n"
            "Use the menu below to get started."
        ),
        "menu_prompt": "What would you like to do?",
        "menu_tips": "⚽ Tips",
        "menu_history": "📜 History",
        "menu_vip": "⭐ VIP",
        "menu_support": "🛠 Support",
        "menu_language": "🌐 Language",
        "tips_title": "📅 Active matches — pick one for analysis:",
        "no_matches": "No active matches right now. Check back soon!",
        "match_not_found": "This match is no longer available.",
        "back": "🔙 Back",
        "vip_coming_soon": "⭐ Our VIP package is coming very soon! Stay tuned.",
        "support_text": (
            "🛠 Support\n\n"
            "For questions, feedback, or partnership inquiries, "
            "reach out to us directly:\n👉 @kamrancamlv"
        ),
        "history_text": (
            "📜 The prediction history section is coming soon.\n"
            "For now, check the 'Tips' section for current matches."
        ),
        "choose_language_prompt": "🌐 Lütfen dilinizi seçin / Please choose your language:",
    },
}
