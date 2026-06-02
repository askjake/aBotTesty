import { HTMLProps } from 'react';
import { SelectOption } from '@shared/ui/types/common.types';
import { ChatType } from '@shared/ui/types/chats.types';

export interface BetaReportsTemplateProps extends HTMLProps<HTMLDivElement> {
  availableDevicesOptions?: SelectOption<string>[];
  availablePlatformsOptions?: SelectOption<string>[];
  activeChat?: ChatType;
  defaultPlatform?: string;
  defaultRelease?: string;
  defaultPriority?: string;
  defaultDevice?: string;
  defaultDateRange?: string[];
  hasAccess: boolean;
}
