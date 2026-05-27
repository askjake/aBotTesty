import {
  combineReducers,
  configureStore,
  EnhancedStore,
} from '@reduxjs/toolkit';
import { HYDRATE } from 'next-redux-wrapper';
import { nextReduxCookieMiddleware } from 'next-redux-cookie-wrapper';

import { DeepPartial } from '@shared/ui/types/common.types';
import { settingsReducer } from '@shared/ui/store/settings/settings.slice';
import { chatsReducer } from '@shared/ui/store/chats/chats.slice';
import { chatsGroupsReducer } from '@shared/ui/store/chatsGroups/chatsGroups.slice';

export type RootState = {
  settings: ReturnType<typeof settingsReducer>;
  chats: ReturnType<typeof chatsReducer>;
  chatsGroups: ReturnType<typeof chatsGroupsReducer>;
};

type MockStore = EnhancedStore<RootState>;

const combinedReducers = combineReducers({
  settings: settingsReducer,
  chats: chatsReducer,
  chatsGroups: chatsGroupsReducer,
});

const reducer = (state: RootState | undefined, action: any) => {
  if (action.type === HYDRATE) {
    return {
      ...state,
      ...action.payload,
    };
  } else {
    return combinedReducers(state, action);
  }
};

export const mockStore = (
  initialState: DeepPartial<RootState> = {},
  options: { serializableCheck?: boolean } = {},
): MockStore => {
  const store = configureStore({
    reducer,
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: options.serializableCheck !== false,
      }).prepend(
        nextReduxCookieMiddleware({
          subtrees: [
            {
              subtree: 'settings.themeMode',
              defaultState: 'light',
            },
            {
              subtree: 'settings.collapsedSidebar',
              defaultState: false,
            },
          ],
        }),
      ),
    preloadedState: initialState,
  }) as MockStore;

  return store;
};
