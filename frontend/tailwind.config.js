/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./App.{js,jsx,ts,tsx}",
    "./app/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      fontFamily: {
        // This links the utility 'font-inter' to the loaded font name
        inter: ["Inter_400Regular"],
        "inter-bold": ["Inter_700Bold"],
      },
    },
  },
  plugins: [],
};
