import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import { create } from 'zustand';
import { createJSONStorage, persist, StateStorage } from 'zustand/middleware';

import type { InterfaceMode, User } from '@/lib/types';

const secureStorage: StateStorage = {
  getItem: async (name) => {
    if (Platform.OS === 'web') {
      return globalThis.localStorage?.getItem(name) ?? null;
    }
    return SecureStore.getItemAsync(name);
  },
  setItem: async (name, value) => {
    if (Platform.OS === 'web') {
      globalThis.localStorage?.setItem(name, value);
      return;
    }
    await SecureStore.setItemAsync(name, value);
  },
  removeItem: async (name) => {
    if (Platform.OS === 'web') {
      globalThis.localStorage?.removeItem(name);
      return;
    }
    await SecureStore.deleteItemAsync(name);
  },
};

type BookingDraft = {
  pickup: string;
  destination: string;
  forSomeoneElse: boolean;
  guestName: string;
  guestPhone: string;
};

type AppState = {
  token: string | null;
  user: User | null;
  mode: InterfaceMode;
  bookingDraft: BookingDraft;
  setSession: (token: string, user: User) => void;
  updateUser: (user: User) => void;
  signOut: () => void;
  setMode: (mode: InterfaceMode) => void;
  setBookingDraft: (draft: Partial<BookingDraft>) => void;
};

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      mode: 'rider',
      bookingDraft: {
        pickup: '',
        destination: '',
        forSomeoneElse: false,
        guestName: '',
        guestPhone: '',
      },
      setSession: (token, user) => set({ token, user }),
      updateUser: (user) => set({ user }),
      signOut: () => set({ token: null, user: null, mode: 'rider' }),
      setMode: (mode) => set({ mode }),
      setBookingDraft: (draft) =>
        set((state) => ({ bookingDraft: { ...state.bookingDraft, ...draft } })),
    }),
    {
      name: 'mobility-session',
      storage: createJSONStorage(() => secureStorage),
      partialize: ({ token, user, mode, bookingDraft }) => ({
        token,
        user,
        mode,
        bookingDraft,
      }),
    },
  ),
);
