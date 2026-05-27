import { DarkModeType } from '@shared/ui/types/common.types';
import { ChatType } from '@shared/ui/types/chats.types';
import { UserType } from '@shared/ui/types/user.types';
import { ReleasesType } from '@shared/ui/types/releases.types';
import { ChatGroupType } from './chatGroup.types';

export type SettingsStore = {
  themeMode: DarkModeType;
  collapsedSidebar: boolean;
  releases: ReleasesType[];
  hasMoreReleases: boolean;
  showReleaseModal: boolean;
  user: UserType;
};

export type ChatsStore = {
  chats: ChatType[];
  activeChat: ChatType | null;
  vaultMode: boolean;
  vaultModeRegistered: boolean;
  showEnableVaultModal: boolean;
  aiTyping: boolean;
  hasMoreChats: boolean;
  totalChats: number;
  hasMoreMessages: boolean;
};

export type ChatsGroupsStore = {
  chatsGroups: ChatGroupType[];
  activeChatGroup: string | null;
};

export type RootStore = {
  settings: SettingsStore;
  chats: ChatsStore;
  chatsGroups: ChatsGroupsStore;
};
