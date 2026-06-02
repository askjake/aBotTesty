import { GetProp, MenuProps, TablePaginationConfig, TableProps } from 'antd';
import { SorterResult } from 'antd/es/table/interface';

export type SuccessResponseType = {
  success: boolean;
};

export type DarkModeType = 'light' | 'dark';

export type PagePropsType<T> = {
  pageProps: T;
};

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type SelectOption<T> = {
  label: string;
  value: T;
};

export type CustomMenuItem = Required<MenuProps>['items'][number] & {
  value: any;
};

export type TableParams = {
  pagination?: TablePaginationConfig;
  sortField?: SorterResult<any>['field'];
  sortOrder?: SorterResult<any>['order'];
  filters?: Parameters<GetProp<TableProps, 'onChange'>>[1];
};
