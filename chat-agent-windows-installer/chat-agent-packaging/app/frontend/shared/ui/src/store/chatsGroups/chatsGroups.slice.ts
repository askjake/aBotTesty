import { createSlice } from '@reduxjs/toolkit';

import { ChatsGroupsStore } from '@shared/ui/types/store.types';
import { ChatGroupType } from '@shared/ui/types/chatGroup.types';

const initialState: ChatsGroupsStore = {
  chatsGroups: [],
  activeChatGroup: 'all',
};

export const chatsGroupsSlice = createSlice({
  name: 'chatsGroups',
  initialState,
  reducers: {
    setChatsGroups: (state, { payload = [] }: { payload: ChatGroupType[] }) => {
      state.chatsGroups = payload;
    },
    setActiveChatGroup: (state, { payload }: { payload: string | null }) => {
      state.activeChatGroup = payload;
    },
  },
});

export const { setChatsGroups, setActiveChatGroup } = chatsGroupsSlice.actions;

export const chatsGroupsReducer = chatsGroupsSlice.reducer;
