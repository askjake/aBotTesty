import { SiderProps } from 'antd';
import { CustomMenuItem } from '@shared/ui/types/common.types';

export interface AppsSidebarProps extends SiderProps {
  menuItems: CustomMenuItem[];
}
