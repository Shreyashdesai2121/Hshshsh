import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'

interface WebSocketContextType {
  socket: WebSocket | null
  isConnected: boolean
  lastMessage: any
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

export const useWebSocket = () => {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

interface WebSocketProviderProps {
  children: ReactNode
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<any>(null)

  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const ws = new WebSocket('ws://localhost:8000/ws')
        
        ws.onopen = () => {
          console.log('WebSocket connected')
          setIsConnected(true)
          setSocket(ws)
        }
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            setLastMessage(data)
          } catch (error) {
            console.error('Error parsing WebSocket message:', error)
          }
        }
        
        ws.onclose = () => {
          console.log('WebSocket disconnected')
          setIsConnected(false)
          setSocket(null)
          // Reconnect after 5 seconds
          setTimeout(connectWebSocket, 5000)
        }
        
        ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          setIsConnected(false)
        }
      } catch (error) {
        console.error('Error connecting WebSocket:', error)
        // Retry after 5 seconds
        setTimeout(connectWebSocket, 5000)
      }
    }

    connectWebSocket()

    return () => {
      if (socket) {
        socket.close()
      }
    }
  }, [])

  return (
    <WebSocketContext.Provider value={{ socket, isConnected, lastMessage }}>
      {children}
    </WebSocketContext.Provider>
  )
}