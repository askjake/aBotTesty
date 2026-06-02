import Dexie, { Table } from 'dexie';

interface DraftMessage {
  chat_id: string;
  message: string;
  updated_at: Date;
}

class DexieDatabase extends Dexie {
  draftMessages!: Table<DraftMessage, string>;

  constructor() {
    super('DexieDatabase');
    this.version(1).stores({
      draftMessages: 'chat_id, updated_at',
    });
  }
}

export const dexieDb = new DexieDatabase();
