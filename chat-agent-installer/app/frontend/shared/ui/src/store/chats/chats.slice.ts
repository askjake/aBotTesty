import { createSlice } from '@reduxjs/toolkit';

import { ChatType } from '@shared/ui/types/chats.types';
import { ChatsStore } from '@shared/ui/types/store.types';

const initialState: ChatsStore = {
  chats: [],
  activeChat: null,
  vaultMode: false,
  vaultModeRegistered: false,
  showEnableVaultModal: false,
  aiTyping: false,
  hasMoreChats: false,
  totalChats: 0,
  hasMoreMessages: false,
};

export const chatsSlice = createSlice({
  name: 'chats',
  initialState,
  reducers: {
    setChats: (state, { payload = [] }: { payload: ChatType[] }) => {
      state.chats = payload;
    },
    setActiveChat: (state, { payload }: { payload: ChatType | null }) => {
      state.activeChat = payload;
    },
    setVaultMode: (state, { payload = false }) => {
      state.vaultMode = payload;
    },
    setHasMoreChats: (state, { payload = false }) => {
      state.hasMoreChats = payload;
    },
    setAiTyping: (state, { payload }: { payload: boolean }) => {
      state.aiTyping = payload;
    },
    setTotalChats: (state, { payload = 0 }: { payload: number }) => {
      state.totalChats = payload;
    },
    setVaultModeRegistered: (state, { payload = false }) => {
      state.vaultModeRegistered = payload;
    },
    setShowEnableVaultModal: (state, { payload = false }) => {
      state.showEnableVaultModal = payload;
    },
    setHasMoreMessages: (state, { payload = false }) => {
      state.hasMoreMessages = payload;
    },
  },
});

export const {
  setChats,
  setActiveChat,
  setVaultMode,
  setHasMoreChats,
  setAiTyping,
  setTotalChats,
  setVaultModeRegistered,
  setShowEnableVaultModal,
  setHasMoreMessages,
} = chatsSlice.actions;

export const chatsReducer = chatsSlice.reducer;
