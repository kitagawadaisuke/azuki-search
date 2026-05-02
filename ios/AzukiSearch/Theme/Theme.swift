import SwiftUI

// mockup から抽出したデザイン トークン
enum AppColor {
    // 背景・サーフェス
    static let bg            = Color(red: 1.00, green: 0.97, blue: 0.91)         // 薄クリーム
    static let bgGradient    = LinearGradient(
        colors: [Color(red: 1.00, green: 0.97, blue: 0.93), Color(red: 1.00, green: 0.91, blue: 0.83)],
        startPoint: .top, endPoint: .bottom
    )
    static let surface       = Color.white
    static let surfaceMuted  = Color(red: 0.98, green: 0.94, blue: 0.86)

    // テキスト
    static let text          = Color(red: 0.18, green: 0.15, blue: 0.13)
    static let textDim       = Color(red: 0.54, green: 0.49, blue: 0.45)
    static let textVeryDim   = Color(red: 0.72, green: 0.68, blue: 0.64)

    // ブランド/アクセント
    static let primaryBlue   = Color(red: 0.36, green: 0.64, blue: 0.84)
    static let primaryPink   = Color(red: 0.95, green: 0.61, blue: 0.71)
    static let warmOrange    = Color(red: 1.00, green: 0.65, blue: 0.40)

    // 番号丸用 5色 (mockup: 1青 / 2緑 / 3橙 / 4紫 / 5青)
    static let numColors: [Color] = [
        Color(red: 0.36, green: 0.64, blue: 0.84),  // blue
        Color(red: 0.43, green: 0.84, blue: 0.71),  // mint
        Color(red: 1.00, green: 0.65, blue: 0.40),  // orange
        Color(red: 0.66, green: 0.59, blue: 0.83),  // purple
        Color(red: 0.36, green: 0.64, blue: 0.84),  // blue (cycle)
    ]

    // タグ chip
    static let tagYellowBg   = Color(red: 0.99, green: 0.94, blue: 0.75)
    static let tagYellowFg   = Color(red: 0.72, green: 0.52, blue: 0.18)
    static let tagBlueBg     = Color(red: 0.83, green: 0.91, blue: 0.96)
    static let tagBlueFg     = Color(red: 0.17, green: 0.48, blue: 0.71)
    static let tagPurpleBg   = Color(red: 0.89, green: 0.86, blue: 0.94)
    static let tagPurpleFg   = Color(red: 0.43, green: 0.36, blue: 0.66)
    static let tagPinkBg     = Color(red: 0.97, green: 0.85, blue: 0.89)
    static let tagPinkFg     = Color(red: 0.72, green: 0.33, blue: 0.47)

    // アイコンsquare bg (ジャンル別)
    static let iconUtaBg     = Color(red: 1.00, green: 0.96, blue: 0.84)
    static let iconCornerBg  = Color(red: 1.00, green: 0.96, blue: 0.84)
    static let iconTaisoBg   = Color(red: 0.91, green: 0.89, blue: 0.96)
    static let iconAnimeBg   = Color(red: 0.85, green: 0.91, blue: 0.96)
    static let iconNingyoBg  = Color(red: 0.97, green: 0.86, blue: 0.91)

    // 曜日色 (mockup: 土=青, 日=赤)
    static let saturdayFg    = Color(red: 0.36, green: 0.64, blue: 0.84)
    static let sundayFg      = Color(red: 0.91, green: 0.35, blue: 0.55)

    // ボーダー
    static let border        = Color(red: 0.91, green: 0.87, blue: 0.83)
}

enum AppRadius {
    static let small: CGFloat  = 10
    static let medium: CGFloat = 14
    static let large: CGFloat  = 20
}

enum AppShadow {
    static let card = (color: Color.black.opacity(0.06), radius: CGFloat(4), x: CGFloat(0), y: CGFloat(2))
    static let small = (color: Color.black.opacity(0.04), radius: CGFloat(2), x: CGFloat(0), y: CGFloat(1))
}

// SwiftUI で使いやすいshadow extension
extension View {
    func appCardShadow() -> some View {
        self.shadow(
            color: AppShadow.card.color,
            radius: AppShadow.card.radius,
            x: AppShadow.card.x,
            y: AppShadow.card.y
        )
    }
}

// ジャンル(corner) → 表示メタ
struct GenreMeta {
    let emoji: String
    let iconBg: Color
    let chipBg: Color
    let chipFg: Color
}

func genreMeta(for corner: String) -> GenreMeta {
    switch corner {
    case "うた":
        return GenreMeta(emoji: "🎵",  iconBg: AppColor.iconUtaBg,    chipBg: AppColor.tagYellowBg, chipFg: AppColor.tagYellowFg)
    case "コーナー":
        return GenreMeta(emoji: "✋",  iconBg: AppColor.iconCornerBg, chipBg: AppColor.tagYellowBg, chipFg: AppColor.tagYellowFg)
    case "体操":
        return GenreMeta(emoji: "🤸",  iconBg: AppColor.iconTaisoBg,  chipBg: AppColor.tagPurpleBg, chipFg: AppColor.tagPurpleFg)
    case "アニメ":
        return GenreMeta(emoji: "📺",  iconBg: AppColor.iconAnimeBg,  chipBg: AppColor.tagBlueBg,   chipFg: AppColor.tagBlueFg)
    case "人形劇":
        return GenreMeta(emoji: "🎭",  iconBg: AppColor.iconNingyoBg, chipBg: AppColor.tagPinkBg,   chipFg: AppColor.tagPinkFg)
    default:
        return GenreMeta(emoji: "🎶", iconBg: AppColor.surfaceMuted, chipBg: AppColor.tagBlueBg, chipFg: AppColor.tagBlueFg)
    }
}
