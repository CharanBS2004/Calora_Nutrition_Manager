import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  // Light Palette
  static const Color primaryLight = Color(0xFF3F7D5A);
  static const Color primaryDarkLight = Color(0xFF2F6547);
  static const Color secondaryLight = Color(0xFF5FAF8A);
  static const Color backgroundLight = Color(0xFFF7F8F3);
  static const Color surfaceLight = Color(0xFFFFFFFF);
  static const Color softSurfaceLight = Color(0xFFEEF4EC);
  static const Color textPrimaryLight = Color(0xFF17231B);
  static const Color textSecondaryLight = Color(0xFF66736A);
  static const Color borderLight = Color(0xFFDCE5DD);

  // Dark Palette
  static const Color backgroundDark = Color(0xFF0D1410);
  static const Color surfaceDark = Color(0xFF151E18);
  static const Color elevatedSurfaceDark = Color(0xFF1D2921);
  static const Color primaryDark = Color(0xFF7CC99A);
  static const Color primaryContainerDark = Color(0xFF214B35);
  static const Color textPrimaryDark = Color(0xFFF2F7F3);
  static const Color textSecondaryDark = Color(0xFFAAB8AE);
  static const Color borderDark = Color(0xFF2B3A31);

  // Nutrition Semantic Macro Colors (Universal)
  static const Color calories = Color(0xFFF27A23);      // Warm Orange / Amber
  static const Color protein = Color(0xFF02A4A8);       // Teal / Cyan
  static const Color carbohydrates = Color(0xFFE5A93C); // Golden Yellow
  static const Color fat = Color(0xFFE06A55);           // Soft Coral
  static const Color fiber = Color(0xFF4E9F3D);         // Leaf Green
  static const Color water = Color(0xFF3880EC);         // Blue
  static const Color activity = Color(0xFF7E57C2);      // Purple / Violet
  static const Color success = Color(0xFF2E7D32);
  static const Color warning = Color(0xFFF57C00);
  static const Color error = Color(0xFFD32F2F);
}

class AppSpacing {
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 12.0;
  static const double lg = 16.0;
  static const double xl = 20.0;
  static const double xxl = 24.0;
  static const double xxxl = 32.0;
}

class AppRadius {
  static const double small = 12.0;
  static const double card = 18.0;
  static const double large = 24.0;
  static const double button = 14.0;
}

class AppTheme {
  static const Color sagePrimary = AppColors.primaryLight;
  static const Color deepTealAccent = AppColors.primaryDarkLight;
  static const Color proteinColor = AppColors.protein;
  static const Color carbColor = AppColors.carbohydrates;
  static const Color fatColor = AppColors.fat;
  static const Color fiberColor = AppColors.fiber;

  static ThemeData get lightTheme {
    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: AppColors.backgroundLight,
      colorScheme: const ColorScheme.light(
        primary: AppColors.primaryLight,
        onPrimary: Colors.white,
        primaryContainer: AppColors.softSurfaceLight,
        secondary: AppColors.secondaryLight,
        background: AppColors.backgroundLight,
        surface: AppColors.surfaceLight,
        onSurface: AppColors.textPrimaryLight,
        error: AppColors.error,
      ),
    );

    return base.copyWith(
      textTheme: GoogleFonts.interTextTheme(base.textTheme).copyWith(
        displayLarge: GoogleFonts.inter(fontSize: 34, fontWeight: FontWeight.bold, color: AppColors.textPrimaryLight),
        displayMedium: GoogleFonts.inter(fontSize: 26, fontWeight: FontWeight.bold, color: AppColors.textPrimaryLight),
        headlineSmall: GoogleFonts.inter(fontSize: 20, fontWeight: FontWeight.w600, color: AppColors.textPrimaryLight),
        titleMedium: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimaryLight),
        bodyLarge: GoogleFonts.inter(fontSize: 15, color: AppColors.textPrimaryLight),
        bodyMedium: GoogleFonts.inter(fontSize: 13, color: AppColors.textSecondaryLight),
        labelSmall: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w500, color: AppColors.textSecondaryLight),
      ),
      cardTheme: CardThemeData(
        color: AppColors.surfaceLight,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.card),
          side: const BorderSide(color: AppColors.borderLight, width: 1),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primaryLight,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.button)),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          textStyle: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surfaceLight,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.button),
          borderSide: const BorderSide(color: AppColors.borderLight),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.button),
          borderSide: const BorderSide(color: AppColors.borderLight),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.button),
          borderSide: const BorderSide(color: AppColors.primaryLight, width: 2),
        ),
      ),
    );
  }

  static ThemeData get darkTheme {
    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppColors.backgroundDark,
      colorScheme: const ColorScheme.dark(
        primary: AppColors.primaryDark,
        onPrimary: AppColors.backgroundDark,
        primaryContainer: AppColors.primaryContainerDark,
        secondary: AppColors.primaryDark,
        background: AppColors.backgroundDark,
        surface: AppColors.surfaceDark,
        onSurface: AppColors.textPrimaryDark,
        error: AppColors.error,
      ),
    );

    return base.copyWith(
      textTheme: GoogleFonts.interTextTheme(base.textTheme).copyWith(
        displayLarge: GoogleFonts.inter(fontSize: 34, fontWeight: FontWeight.bold, color: AppColors.textPrimaryDark),
        displayMedium: GoogleFonts.inter(fontSize: 26, fontWeight: FontWeight.bold, color: AppColors.textPrimaryDark),
        headlineSmall: GoogleFonts.inter(fontSize: 20, fontWeight: FontWeight.w600, color: AppColors.textPrimaryDark),
        titleMedium: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimaryDark),
        bodyLarge: GoogleFonts.inter(fontSize: 15, color: AppColors.textPrimaryDark),
        bodyMedium: GoogleFonts.inter(fontSize: 13, color: AppColors.textSecondaryDark),
        labelSmall: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w500, color: AppColors.textSecondaryDark),
      ),
      cardTheme: CardThemeData(
        color: AppColors.surfaceDark,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.card),
          side: const BorderSide(color: AppColors.borderDark, width: 1),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primaryDark,
          foregroundColor: AppColors.backgroundDark,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.button)),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          textStyle: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surfaceDark,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.button),
          borderSide: const BorderSide(color: AppColors.borderDark),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.button),
          borderSide: const BorderSide(color: AppColors.borderDark),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.button),
          borderSide: const BorderSide(color: AppColors.primaryDark, width: 2),
        ),
      ),
    );
  }
}
