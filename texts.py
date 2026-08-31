TEXTS = {
    "tr": {
        "choose_language": "Lütfen dilinizi seçin:",
        "welcome": (
            "🎯 *Hoş geldin, {name}!*\n\n"
            "Ben **Statify Bet AI** – yapay zeka destekli futbol tahmin botuyum.\n"
            "Günlük maçları istatistiksel modellerle analiz ediyor, kazanan takım, "
            "her iki takımın gol atması (KG) ve toplam gol sayısı (Üst/Alt) gibi "
            "ana piyasalara yönelik tahminler sunuyorum.\n\n"
            "📊 *Başarı Oranımız:* %%92\n"
            "✅ Tüm tahminler veriye dayalıdır."
        ),
        "menu_prompt": "Ana menüden bir seçenek belirleyin:",
        "menu_tips": "📊 Tahminler",
        "menu_history": "📜 Geçmiş",
        "menu_vip": "⭐ VIP",
        "menu_support": "🆘 Destek",
        "menu_language": "🌐 Dil",
        "tips_title": "📊 Bugünün Tahminleri (Normal):\nAşağıdan bir maç seçin.",
        "vip_title": "⭐ VIP Tahminler:\nAşağıdan bir VIP maçı seçin.",
        "no_matches": "⚠️ Henüz bu kategoride tahmin eklenmemiş.",
        "back": "◀️ Geri",
        "match_not_found": "Maç bulunamadı.",
        "history_text": "📜 *Geçmiş maçlar:*\n{matches}",
        "no_history": "Henüz geçmiş maç bulunmuyor.",
        "vip_coming_soon": "⭐ VIP tahminler yakında!",
        "support_prompt": (
            "🆘 Destek ekibimize mesaj göndermek için aşağıya yazabilirsiniz.\n"
            "Mesajınız 1-24 saat içinde cevaplandırılacaktır."
        ),
        "support_thanks": (
            "✅ Mesajınız alındı. En kısa sürede (1-24 saat) size dönüş yapılacaktır."
        ),
        "support_reply": "📩 Destek ekibinden yanıt:\n\n{reply_text}",
        "admin_notify": "📩 Yeni destek mesajı!\nKullanıcı: {user}\nMesaj: {msg}",
        "error_generic": "Bir hata oluştu, lütfen tekrar deneyin.",
        "add_match_date": "📅 Maçın tarih ve saatini UTC ile gönderin (örnek: 30.08 20:00 (UTC+4)):",
        "add_match_league": "🏆 Liqayı gönderin:",
        "add_match_home": "🏠 Ev sahibi takımı gönderin:",
        "add_match_away": "✈️ Deplasman takımını gönderin:",
        "add_match_prediction": "📊 Tahmin metnini gönderin (örnek: Ev sahibi kazanır):",
        "add_match_analysis": "📝 Analiz metnini gönderin (örnek: Son 5 maçta 4 galibiyet...):",
        "add_match_category": "🗂️ Bu tahmini hangi kategoriye ekleyelim?",
        "category_normal": "📊 Normal",
        "category_vip": "⭐ VIP",
        "match_added": "✅ Maç başarıyla eklendi! ID: {match_id}",
        "match_deleted": "✅ Maç silindi.",
        "match_list": "📋 Mevcut maçlar:\n{list}",
        "no_matches_list": "Henüz maç yok.",
        "admin_denied": "❌ Bu komutu yalnız admin kullanabilir.",
        "delete_match_usage": "Kullanım: /deletematch <match_id>",
        "reply_usage": "Kullanım: /reply <ticket_id> <cevap>",
    },
    "en": {
        "choose_language": "Please select your language:",
        "welcome": (
            "🎯 *Welcome, {name}!*\n\n"
            "I am **Statify Bet AI** – an AI-powered football prediction bot.\n"
            "I analyze daily matches using statistical models and provide tips "
            "for Match Winner, BTTS, and Over/Under goals.\n\n"
            "📊 *Success Rate:* 92%%\n"
            "✅ All predictions are data-driven."
        ),
        "menu_prompt": "Choose an option from the main menu:",
        "menu_tips": "📊 Tips",
        "menu_history": "📜 History",
        "menu_vip": "⭐ VIP",
        "menu_support": "🆘 Support",
        "menu_language": "🌐 Language",
        "tips_title": "📊 Today's Tips (Normal):\nSelect a match below.",
        "vip_title": "⭐ VIP Tips:\nSelect a VIP match below.",
        "no_matches": "⚠️ No predictions in this category yet.",
        "back": "◀️ Back",
        "match_not_found": "Match not found.",
        "history_text": "📜 *Past matches:*\n{matches}",
        "no_history": "No past matches yet.",
        "vip_coming_soon": "⭐ VIP tips coming soon!",
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
        "add_match_date": "📅 Send match date and time in UTC (e.g. 30.08 20:00 (UTC+4)):",
        "add_match_league": "🏆 Send league name:",
        "add_match_home": "🏠 Send home team:",
        "add_match_away": "✈️ Send away team:",
        "add_match_prediction": "📊 Send prediction text (e.g. Home wins):",
        "add_match_analysis": "📝 Send analysis text (e.g. Last 5 matches, 4 wins...):",
        "add_match_category": "🗂️ Which category to add this tip to?",
        "category_normal": "📊 Normal",
        "category_vip": "⭐ VIP",
        "match_added": "✅ Match added! ID: {match_id}",
        "match_deleted": "✅ Match deleted.",
        "match_list": "📋 Current matches:\n{list}",
        "no_matches_list": "No matches yet.",
        "admin_denied": "❌ This command is for admin only.",
        "delete_match_usage": "Usage: /deletematch <match_id>",
        "reply_usage": "Usage: /reply <ticket_id> <reply>",
    }
}
