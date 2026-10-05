import { createContext } from 'react'
import type { User } from '../../types'

export type Auth = {
  user: User | null
  login: (email: string, password: string) => Promise<User>
  register: (name: string, email: string, password: string) => Promise<User>
  logout: () => void
}

export const AuthContext = createContext<Auth | null>(null)
