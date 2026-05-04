import SwiftUI

struct ContentView: View {
    @StateObject private var dataStore = DataStore()
    @StateObject private var favs = FavoritesStore()
    @StateObject private var memos = MemoStore()

    @State private var selectedTab: Int = 0

    init() {
        // TabBar の見た目をmockup風に微調整
        let app = UITabBarAppearance()
        app.configureWithOpaqueBackground()
        app.backgroundColor = UIColor.white
        app.shadowColor = UIColor(red: 0.91, green: 0.87, blue: 0.83, alpha: 1.0)

        let activeColor = UIColor(red: 0.36, green: 0.64, blue: 0.84, alpha: 1.0)
        let inactiveColor = UIColor(red: 0.54, green: 0.49, blue: 0.45, alpha: 1.0)
        app.stackedLayoutAppearance.normal.iconColor = inactiveColor
        app.stackedLayoutAppearance.normal.titleTextAttributes = [.foregroundColor: inactiveColor]
        app.stackedLayoutAppearance.selected.iconColor = activeColor
        app.stackedLayoutAppearance.selected.titleTextAttributes = [.foregroundColor: activeColor]

        UITabBar.appearance().standardAppearance = app
        UITabBar.appearance().scrollEdgeAppearance = app
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeView()
                .tabItem {
                    Label("ホーム", systemImage: "house.fill")
                }
                .tag(0)

            DateSearchView()
                .tabItem {
                    Label("日付検索", systemImage: "calendar")
                }
                .tag(1)

            KeywordSearchView()
                .tabItem {
                    Label("キーワード検索", systemImage: "magnifyingglass")
                }
                .tag(2)

            FavoritesView()
                .tabItem {
                    Label("お気に入り", systemImage: "heart.fill")
                }
                .tag(3)
        }
        .environmentObject(dataStore)
        .environmentObject(favs)
        .environmentObject(memos)
        .task {
            await dataStore.load()
        }
    }
}

#Preview {
    ContentView()
}
