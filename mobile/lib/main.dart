import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/services/notification_service.dart';
import 'core/theme/app_theme.dart';
import 'providers/app_providers.dart';
import 'ui/screens/auth_screens.dart';
import 'ui/screens/home_screen.dart';
import 'ui/screens/log_food_screen.dart';
import 'ui/screens/recipe_library_screen.dart';
import 'ui/screens/analytics_screen.dart';
import 'ui/screens/coach_screen.dart';
import 'ui/screens/profile_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => NutritionProvider()),
        ChangeNotifierProvider(create: (_) => CoachProvider()),
      ],
      child: const NutritionCoachApp(),
    ),
  );

  unawaited(_initializeNotifications());
}

Future<void> _initializeNotifications() async {
  try {
    final notifService = NotificationService();
    await notifService.initialize();
    await notifService.scheduleBackgroundChecks(enabled: true);
  } catch (e) {
    debugPrint("Notification service initialization error: $e");
  }
}

class NutritionCoachApp extends StatelessWidget {
  const NutritionCoachApp({super.key});

  @override
  Widget build(BuildContext context) {
    final themeProvider = Provider.of<ThemeProvider>(context);

    return MaterialApp(
      title: 'Calora',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: themeProvider.themeMode,
      routes: {
        '/': (_) => const RootAuthGate(),
        '/home': (_) => const MainNavigationShell(initialIndex: 0),
        '/log': (_) => const LogFoodScreen(),
        '/recipes': (_) => const RecipeLibraryScreen(),
        '/analytics': (_) => const AnalyticsScreen(),
        '/coach': (_) => const CoachScreen(),
        '/profile': (_) => const ProfileScreen(),
      },
    );
  }
}

class RootAuthGate extends StatefulWidget {
  const RootAuthGate({super.key});

  @override
  State<RootAuthGate> createState() => _RootAuthGateState();
}

class _RootAuthGateState extends State<RootAuthGate> {
  late Future<bool> _autoLoginFuture;

  @override
  void initState() {
    super.initState();
    _autoLoginFuture = Provider.of<AuthProvider>(context, listen: false)
        .tryAutoLogin()
        .timeout(const Duration(seconds: 6), onTimeout: () => false);
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthProvider>(
      builder: (context, auth, _) {
        if (auth.isAuthenticated) {
          return const MainNavigationShell();
        }

        return FutureBuilder<bool>(
          future: _autoLoginFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return Scaffold(
                body: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        width: 64,
                        height: 64,
                        decoration: BoxDecoration(
                          color: AppTheme.sagePrimary.withOpacity(0.15),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.eco_rounded,
                            color: AppTheme.sagePrimary, size: 36),
                      ),
                      const SizedBox(height: 16),
                      const CircularProgressIndicator(
                          color: AppTheme.sagePrimary),
                    ],
                  ),
                ),
              );
            }

            if (snapshot.data == true) {
              return const MainNavigationShell();
            }

            return const AuthScreen();
          },
        );
      },
    );
  }
}

class MainNavigationShell extends StatefulWidget {
  final int initialIndex;

  const MainNavigationShell({super.key, this.initialIndex = 0});

  @override
  State<MainNavigationShell> createState() => _MainNavigationShellState();
}

class _MainNavigationShellState extends State<MainNavigationShell> {
  late int _currentIndex;

  final List<Widget> _screens = const [
    HomeScreen(),
    RecipeLibraryScreen(),
    AnalyticsScreen(),
    CoachScreen(),
    ProfileScreen(),
  ];

  @override
  void initState() {
    super.initState();
    _currentIndex = widget.initialIndex;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      floatingActionButton: FloatingActionButton(
        heroTag: 'fab_log_meal',
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const LogFoodScreen()),
          );
        },
        backgroundColor: AppTheme.sagePrimary,
        foregroundColor: Colors.white,
        elevation: 3,
        tooltip: "Log Food",
        child: const Icon(Icons.add_rounded, size: 28),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.miniEndDocked,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (idx) {
          setState(() => _currentIndex = idx);
        },
        indicatorColor: theme.colorScheme.primary.withOpacity(0.18),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard_rounded),
            label: "Home",
          ),
          NavigationDestination(
            icon: Icon(Icons.menu_book_outlined),
            selectedIcon: Icon(Icons.menu_book_rounded),
            label: "Recipes",
          ),
          NavigationDestination(
            icon: Icon(Icons.insights_outlined),
            selectedIcon: Icon(Icons.insights_rounded),
            label: "Analytics",
          ),
          NavigationDestination(
            icon: Icon(Icons.psychology_outlined),
            selectedIcon: Icon(Icons.psychology_rounded),
            label: "Coach",
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline_rounded),
            selectedIcon: Icon(Icons.person_rounded),
            label: "Profile",
          ),
        ],
      ),
    );
  }
}
