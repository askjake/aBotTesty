import { LayoutProps } from 'antd';
import { CustomMenuItem } from '@shared/ui/types/common.types';

export interface AppsContainerProps extends LayoutProps {
  menuItems: CustomMenuItem[];
}
