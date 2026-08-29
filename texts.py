# texts.py
TEXTS = {
    "tr": {
        "choose_language_prompt": (
            "🎯 *Hoş geldin, {name}!*\n\n"
            "Ben **Statify Bet AI** – yapay zeka destekli futbol tahmin botuyum.\n"
            "Günlük maçları istatistiksel modellerle analiz ediyor, kazanan takım, "
            "her iki takımın gol atması (KG) ve toplam gol sayısı (Üst/Alt) gibi "
            "ana piyasalara yönelik tahminler sunuyorum.\n\n"
            "📊 *Başarı Oranımız:* %%92\n"
            "✅ Tüm tahminler veriye dayalıdır.\n\n"
            "Devam etmek için lütfen dilinizi seçin:"
        ),
        "welcome": "Hoş geldin, {name}!",
        "menu_prompt": "Ana menüden bir seçenek belirleyin:",
        "menu_tips": "📊 Tahminler",
        "menu_history": "📜 Geçmiş",
        "menu_vip": "⭐ VIP",
        "menu_support": "🆘 Destek",
        "menu_language": "🌐 Dil",
        "tips_title": "📊 Bugünün Tahminleri:\nAşağıdan bir maç seçin.",
        "no_matches": "⚠️ Henüz tahmin eklenmemiş.",
        "back": "◀️ Geri",
        "match_not_found": "Maç bulunamadı.",
        "history_text": "📜 *Geçmiş maçlar:*\n{matches}",
        "no_history": "Henüz geçmiş maç bulunmuyor.",
        "vip_coming_soon": "⭐ VIP hizmetlerimiz çok yakında! Özel tahminler ve analizler için bizi takip edin.",
        "support_prompt": (
            "🆘 Destek ekibimize mesaj göndermek için aşağıya yazabilirsiniz.\n"
            "Mesajınız 1-24 saat içinde cevaplandırılacaktır."
        ),
        "support_thanks": (
            "✅ Mesajınız alındı. En kısa sürede (1-24 saat) size dönüş yapılacaktır."
        ),
        "support_reply": "📩 Destek ekibinden yanıt:\n\n{reply_text}",
        "admin_notify": "📩 Yeni destek mesajı var!\nKullanıcı: {user}\nMesaj: {msg}\nBu mesaja doğrudan yanıt vererek cevap gönderebilirsiniz.",
        "error_generic": "Bir hata oluştu, lütfen tekrar deneyin.",
        "add_match_usage": (
            "Kullanım: /addmatch <tarih> <lig> <ev> <deplasman> | <tr_tahmin> | <en_tahmin>\n"
            "Örnek: /addmatch 29.08 20:00 (UTC+3) | Premier Lig | Takım A | Takım B | Ev sahibi kazanır | Home win"
        ),
        "match_added": "✅ Maç başarıyla eklendi! ID: {match_id}",
        "edit_match_usage": "Kullanım: /editmatch <match_id> <yeni_tarih> <yeni_lig> ...",
        "delete_match_usage": "Kullanım: /deletematch <match_id>",
        "match_deleted": "✅ Maç silindi.",
        "match_list": "📋 Mevcut maçlar:\n{list}",
        "no_matches_list": "Henüz maç yok.",
    },
    "en": {
        "choose_language_prompt": (
            "🎯 *Welcome, {name}!*\n\n"
            "I am **Statify Bet AI** – an AI-powered football prediction bot.\n"
            "I analyze daily matches using statistical models and provide tips "
            "for Match Winner, Both Teams to Score (BTTS), and Over/Under goals.\n\n"
            "📊 *Success Rate:* 92%%\n"
            "✅ All predictions are data-driven.\n\n"
            "Please select your language:"
        ),
        "welcome": "Welcome, {name}!",
        "menu_prompt": "Choose an option from the main menu:",
        "menu_tips": "📊 Tips",
        "menu_history": "📜 History",
        "menu_vip": "⭐ VIP",
        "menu_support": "🆘 Support",
        "menu_language": "🌐 Language",
        "tips_title": "📊 Today's Tips:\nSelect a match below.",
        "no_matches": "⚠️ No predictions added yet.",
        "back": "◀️ Back",
        "match_not_found": "Match not found.",
        "history_text": "📜 *Past matches:*\n{matches}",
        "no_history": "No past matches yet.",
        "vip_coming_soon": "⭐ VIP services coming soon! Stay tuned.",
        "support_prompt": (
            "🆘 Write your message to our support team below.\n"
            "Your message will be replied within 1-24 hours."
        ),
        "support_thanks": (
            "✅ Your message has been received. We will reply within 1-24 hours."
        ),
        "support_reply": "📩 Support team reply:\n\n{reply_text}",
        "admin_notify": "📩 New support message!\nUser: {user}\nMessage: {msg}",
        "error_generic": "An error occurred, please try again.",
        "add_match_usage": (
            "Usage: /addmatch <date> <league> <home> <away> | <tr_pred> | <en_pred>\n"
            "Example: /addmatch 29.08 20:00 (UTC+3) | Premier League | Team A | Team B | Home wins | Home win"
        ),
        "match_added": "✅ Match added! ID: {match_id}",
        "edit_match_usage": "Usage: /editmatch <match_id> ...",
        "delete_match_usage": "Usage: /deletematch <match_id>",
        "match_deleted": "✅ Match deleted.",
        "match_list": "📋 Current matches:\n{list}",
        "no_matches_list": "No matches yet.",
    }
}
