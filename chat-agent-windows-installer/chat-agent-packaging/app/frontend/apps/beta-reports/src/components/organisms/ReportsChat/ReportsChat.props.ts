import { CardProps } from 'antd';
import { ChatType } from '@shared/ui/types/chats.types';
import { RefObject } from 'react';

export interface ReportsChatRef {
  refetchData: () => Promise<void>;
}

export interface ReportsChatProps extends CardProps {
  chat: ChatType;
  platform?: string;
  componentRef: RefObject<ReportsChatRef | null>;
}
