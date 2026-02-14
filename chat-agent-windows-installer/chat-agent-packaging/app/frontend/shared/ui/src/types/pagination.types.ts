export type PaginationType<T> = {
  docs: T[];
  totalDocs: number;
  limit: number;
  page: number;
  totalPages: number;
  hasNextPage: boolean;
  nextPage: number;
  hasPrevPage: boolean;
  prevPage: number;
};

export type PaginationProps = {
  limit: number;
  page: number;
  search?: string;
};
