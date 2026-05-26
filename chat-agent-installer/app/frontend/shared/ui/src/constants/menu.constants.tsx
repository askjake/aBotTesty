import {
  AppstoreOutlined,
  MessageOutlined,
  SafetyOutlined,
  FileTextOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import Link from 'next/link';

export interface MenuItemWithValue {
  key: string;
  label?: React.ReactNode;
  value?: string;
  icon?: React.ReactNode;
  type?: 'divider' | 'group';
  children?: MenuItemWithValue[];
}

export const MENU_ITEMS: MenuItemWithValue[] = [
  {
    key: '1',
    label: <Link href='/'>Chats</Link>,
    value: '/',
    icon: <MessageOutlined />,
  },
  {
    key: '2',
    label: <Link href='/apps'>Apps</Link>,
    value: '/apps',
    icon: <AppstoreOutlined />,
  },
  {
    key: '3',
    label: <Link href='/vault-mode'>Vault Mode Settings</Link>,
    value: '/vault-mode',
    icon: <SafetyOutlined />,
  },
  {
    key: 'workbench-divider',
    type: 'divider',
  },
  {
    key: 'workbench-group',
    label: 'Workbench',
    type: 'group',
    children: [
      {
        key: '4',
        label: <Link href='/chat-tools/journals'>Chat Summaries</Link>,
        value: '/chat-tools/journals',
        icon: <FileTextOutlined />,
      },
      {
        key: '5',
        label: <Link href='/runs'>Automation Runs</Link>,
        value: '/runs',
        icon: <CodeOutlined />,
      },
    ],
  },
];
