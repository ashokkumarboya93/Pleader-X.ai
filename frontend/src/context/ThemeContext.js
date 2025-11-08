import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

export const themes = {
  green: {
    name: 'Green',
    primary: '#10b981',
    primaryHover: '#059669',
    primaryLight: '#d1fae5',
    bgGradient: 'from-green-50 to-green-100'
  },
  blue: {
    name: 'Blue',
    primary: '#3b82f6',
    primaryHover: '#2563eb',
    primaryLight: '#dbeafe',
    bgGradient: 'from-blue-50 to-blue-100'
  },
  purple: {
    name: 'Purple',
    primary: '#a855f7',
    primaryHover: '#9333ea',
    primaryLight: '#f3e8ff',
    bgGradient: 'from-purple-50 to-purple-100'
  },
  orange: {
    name: 'Orange',
    primary: '#f97316',
    primaryHover: '#ea580c',
    primaryLight: '#ffedd5',
    bgGradient: 'from-orange-50 to-orange-100'
  },
  pink: {
    name: 'Pink',
    primary: '#ec4899',
    primaryHover: '#db2777',
    primaryLight: '#fce7f3',
    bgGradient: 'from-pink-50 to-pink-100'
  },
  indigo: {
    name: 'Indigo',
    primary: '#6366f1',
    primaryHover: '#4f46e5',
    primaryLight: '#e0e7ff',
    bgGradient: 'from-indigo-50 to-indigo-100'
  }
};

export const ThemeProvider = ({ children }) => {
  const [currentTheme, setCurrentTheme] = useState('green');

  useEffect(() => {
    // Load theme from localStorage
    const savedTheme = localStorage.getItem('pleader-theme');
    if (savedTheme && themes[savedTheme]) {
      setCurrentTheme(savedTheme);
    }
  }, []);

  const changeTheme = (themeName) => {
    if (themes[themeName]) {
      setCurrentTheme(themeName);
      localStorage.setItem('pleader-theme', themeName);
    }
  };

  const theme = themes[currentTheme];

  return (
    <ThemeContext.Provider value={{ theme, currentTheme, changeTheme, themes }}>
      <div 
        style={{
          '--theme-primary': theme.primary,
          '--theme-primary-hover': theme.primaryHover,
          '--theme-primary-light': theme.primaryLight,
        }}
        className="theme-wrapper"
      >
        {children}
      </div>
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};
