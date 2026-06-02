import customDayjs from '@shared/ui/libs/dayjs.libs';

import { ChatType } from '@shared/ui/types/chats.types';

export const sortChats = (chats: ChatType[] = []) => {
  return [...chats].sort((a, b) => {
    if (b.active !== a.active) {
      return +b.active - +a.active;
    }
    if (b.favorite !== a.favorite) {
      return +b.favorite - +a.favorite;
    }

    const dateA = a.last_message_at
      ? customDayjs(a.last_message_at)
      : customDayjs(0);
    const dateB = b.last_message_at
      ? customDayjs(b.last_message_at)
      : customDayjs(0);

    return dateB.isAfter(dateA) ? 1 : -1;
  });
};

export const defineGroup = ({
  favorite = false,
  active = false,
  last_message_at,
}: Pick<ChatType, 'favorite' | 'last_message_at' | 'active'>) => {
  if (active) {
    return 'Active';
  }
  if (favorite) {
    return 'Favorites';
  }

  const date = customDayjs(last_message_at);
  const now = customDayjs();
  if (date.isToday()) {
    return 'Today';
  }
  if (date.isYesterday()) {
    return 'Yesterday';
  }
  if (date.isSameOrAfter(now.subtract(7, 'day'))) {
    return 'Previous 7 days';
  }
  if (date.isSameOrAfter(now.subtract(30, 'day'))) {
    return 'Previous 30 days';
  }
  return 'Older';
};
