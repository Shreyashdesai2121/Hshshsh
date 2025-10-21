import React, { createContext, useContext, ReactNode } from 'react'

interface ApiContextType {
  baseUrl: string
}

const ApiContext = createContext<ApiContextType | undefined>(undefined)

export const useApi = () => {
  const context = useContext(ApiContext)
  if (!context) {
    throw new Error('useApi must be used within an ApiProvider')
  }
  return context
}

interface ApiProviderProps {
  children: ReactNode
}

export const ApiProvider: React.FC<ApiProviderProps> = ({ children }) => {
  // Use direct Render backend URL instead of Netlify redirects
  const baseUrl = 'https://hshshsh-b07n.onrender.com/api'

  return (
    <ApiContext.Provider value={{ baseUrl }}>
      {children}
    </ApiContext.Provider>
  )
}