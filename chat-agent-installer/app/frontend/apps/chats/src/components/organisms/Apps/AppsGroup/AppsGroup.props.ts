import { HTMLProps } from 'react';
import { AppsItemType } from '@/types/apps.types';

export type AppsGroupProps = HTMLProps<HTMLDivElement> & {
  title: string;
  items: AppsItemType[];
};
