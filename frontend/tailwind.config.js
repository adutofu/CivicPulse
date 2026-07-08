module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Citizen theme
        'primary-citizen': '#D42F1F',
        'secondary-citizen': '#1B4B3E',
        
        // Government theme
        'primary-govt': '#00D4FF',
        'secondary-govt': '#0A1428',
        
        // Status colors
        'success': '#28a745',
        'warning': '#ffc107',
        'error': '#dc3545',
        'info': '#17a2b8',
      },
    },
  },
  plugins: [],
}
