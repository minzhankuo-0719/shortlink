/** @type {import('tailwindcss').Config} */
module.exports = {
  // Scan every template for class names so the build keeps exactly the classes
  // we use and purges the rest. All our classes live in templates (none are
  // built in Python or by string concatenation in JS), so this glob is complete.
  content: ["./templates/**/*.html"],
  // Dark mode is toggled by adding/removing the `dark` class on <html>
  // (see the theme script in templates/base.html), not by the OS preference.
  darkMode: "class",
  theme: { extend: {} },
  plugins: [],
};
