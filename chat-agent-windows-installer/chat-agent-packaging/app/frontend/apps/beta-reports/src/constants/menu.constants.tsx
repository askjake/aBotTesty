import {
  AppstoreOutlined,
  MessageOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import { CustomMenuItem } from '@shared/ui/types/common.types';

export const BETA_REPORTS_MENU_ITEMS: CustomMenuItem[] = [
  {
    key: '1',
    label: <a href='/'>Chats</a>,
    value: '/chats',
    icon: <MessageOutlined />,
  },
  {
    key: '2',
    label: <a href='/apps'>Apps</a>,
    value: '/',
    icon: <AppstoreOutlined />,
  },
  {
    key: '3',
    label: <a href='/vault-mode'>Vault Mode Settings</a>,
    value: '/vault-mode',
    icon: <SafetyOutlined />,
  },
];
