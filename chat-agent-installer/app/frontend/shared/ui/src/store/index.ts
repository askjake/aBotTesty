import {
  Action,
  combineReducers,
  configureStore,
  ThunkAction,
} from '@reduxjs/toolkit';
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';
import { createWrapper, HYDRATE } from 'next-redux-wrapper';
import {
  nextReduxCookieMiddleware,
  wrapMakeStore,
} from 'next-redux-cookie-wrapper';

import { settingsReducer } from '@shared/ui/store/settings/settings.slice';
import { chatsGroupsReducer } from '@shared/ui/store/chatsGroups/chatsGroups.slice';
import { chatsReducer } from '@shared/ui/store/chats/chats.slice';

import { RootStore } from '@shared/ui/types/store.types';

const combinedReducers = combineReducers({
  settings: settingsReducer,
  chats: chatsReducer,
  chatsGroups: chatsGroupsReducer,
});

const reducer = (state: RootStore, action: any) => {
  if (action.type === HYDRATE) {
    return {
      ...state,
      ...action.payload,
      settings: {
        ...state.settings,
        ...action.payload.settings,
      },
    };
  } else {
    return combinedReducers(state, action);
  }
};

export const makeStore = wrapMakeStore(() =>
  configureStore({
    reducer,
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().prepend(
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
  }),
);

export type AppStore = ReturnType<typeof makeStore>;
export type AppState = ReturnType<AppStore['getState']>;
export type AppDispatch = AppStore['dispatch'];
export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  AppState,
  unknown,
  Action
>;

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootStore> = useSelector;

export const wrapper = createWrapper<AppStore>(makeStore);
