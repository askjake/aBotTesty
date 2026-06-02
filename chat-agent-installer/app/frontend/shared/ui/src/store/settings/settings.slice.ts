import { createSlice } from '@reduxjs/toolkit';
import { SettingsStore } from '@shared/ui/types/store.types';
import { ReleasesType } from '@shared/ui/types/releases.types';
import { UserType } from '@shared/ui/types/user.types';

const initialState: SettingsStore = {
  themeMode: 'light',
  collapsedSidebar: false,
  releases: [],
  hasMoreReleases: false,
  showReleaseModal: false,
  user: {
    first_name: '',
    last_name: '',
    email: '',
    last_release_date: null,
  },
};

export const settingsSlice = createSlice({
  name: 'settings',
  initialState,
  reducers: {
    setUser: (state, { payload }: { payload: UserType }) => {
      state.user = payload;
    },
    toggleThemeMode: (state) => {
      state.themeMode = state.themeMode === 'light' ? 'dark' : 'light';
    },
    toggleSideBar: (state) => {
      state.collapsedSidebar = !state.collapsedSidebar;
    },
    setReleases: (state, { payload = [] }: { payload: ReleasesType[] }) => {
      state.releases = payload;
    },
    setShowReleaseModal: (state, { payload = false }: { payload: boolean }) => {
      state.showReleaseModal = payload;
    },
    setHasMoreReleases: (state, { payload = false }: { payload: boolean }) => {
      state.hasMoreReleases = payload;
    },
  },
});

export const {
  toggleThemeMode,
  toggleSideBar,
  setReleases,
  setUser,
  setShowReleaseModal,
  setHasMoreReleases,
} = settingsSlice.actions;

export const settingsReducer = settingsSlice.reducer;
