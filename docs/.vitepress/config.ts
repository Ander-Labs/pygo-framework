import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'PyGo',
  description: 'A lightweight Go + Python HTMX framework',
  
  themeConfig: {
    nav: [
      { text: 'Docs', link: '/introduction' },
      { text: 'GitHub', link: 'https://github.com/Ander-Labs/pygo-framework' },
    ],
    
    sidebar: [
      {
        text: 'Getting Started',
        items: [
          { text: 'Introduction', link: '/introduction' },
          { text: 'Installation', link: '/installation' },
          { text: 'Quick Start', link: '/quickstart' },
        ]
      },
      {
        text: 'Core',
        items: [
          { text: 'DSL Specification', link: '/dsl' },
          { text: 'Architecture', link: '/architecture' },
          { text: 'Models', link: '/models' },
        ]
      },
      {
        text: 'Features',
        items: [
          { text: 'Authentication', link: '/auth' },
          { text: 'Admin Panel', link: '/admin' },
          { text: 'API', link: '/api' },
          { text: 'Database', link: '/database' },
        ]
      },
      {
        text: 'Advanced',
        items: [
          { text: 'Modules', link: '/modules' },
          { text: 'Jobs', link: '/jobs' },
          { text: 'Email', link: '/email' },
          { text: 'Reports', link: '/reports' },
        ]
      }
    ],
    
    social: {
      github: 'Ander-Labs/pygo-framework'
    }
  }
})