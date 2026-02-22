import "../global.css";

import {
  DarkTheme,
  DefaultTheme,
  ThemeProvider,
} from "@react-navigation/native";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { verifyInstallation } from "nativewind";
import { useEffect } from "react";
import "react-native-reanimated";

import {
  Inter_400Regular,
  Inter_600SemiBold,
  Inter_700Bold,
  useFonts,
} from "@expo-google-fonts/inter";

import { useColorScheme } from "@/hooks/use-color-scheme";

// Prevent the splash screen from auto-hiding
SplashScreen.preventAutoHideAsync();

// Create a custom Light Theme to force the background to pure white
const CustomLightTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: "#ffffff", // This makes the "entire screen" white
    card: "#ffffff",
  },
};

const CustomDarkTheme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: "#000000", // This makes the "entire screen" black
    card: "#000000",
  },
};

export const unstable_settings = {
  anchor: "(tabs)",
};

export default function RootLayout() {
  const colorScheme = useColorScheme();

  const [loaded, error] = useFonts({
    Inter: Inter_400Regular,
    "Inter-SemiBold": Inter_600SemiBold,
    "Inter-Bold": Inter_700Bold,
    interbold: Inter_700Bold,
  });

  useEffect(() => {
    if (__DEV__) {
      try {
        verifyInstallation();
      } catch (e) {
        console.warn(e);
      }
    }

    if (loaded || error) {
      SplashScreen.hideAsync();
    }
  }, [loaded, error]);

  if (!loaded && !error) {
    return null;
  }

  // Choose theme based on colorScheme
  const theme = colorScheme === "dark" ? CustomDarkTheme : CustomLightTheme;

  return (
    <ThemeProvider value={theme}>
      <Stack>
        <Stack.Screen name="(auth)" options={{ headerShown: false }} />
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen
          name="modal"
          options={{ presentation: "modal", title: "Modal" }}
        />
      </Stack>
      {/* Set status bar to dark icons if we are in light mode (white background) */}
      <StatusBar style={colorScheme === "dark" ? "light" : "dark"} />
    </ThemeProvider>
  );
}
